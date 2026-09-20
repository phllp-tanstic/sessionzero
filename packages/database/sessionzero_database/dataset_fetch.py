"""Bounded, resumable collection. Archives are private; stdout contains counts only."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sessionzero_bitget import BitgetMarketClient, BitgetReferenceDataProvider
from sessionzero_bitget.history import fetch_bounded_history
from sessionzero_market_data import CuratedBitgetSourceSessionProvider
from sessionzero_market_data.alpaca import AlpacaNativeEquityProvider
from sessionzero_market_data.native import NativeDataError

from .dataset_artifacts import encode_history, target_date, write_json
from .native_cohort import reverify_native_cohort


class RequestGate:
    """One gate shared by every worker and every retry: at most 188 requests/minute."""

    def __init__(self):
        self.lock = threading.Lock()
        self.previous = 0.0

    def wait(self):
        with self.lock:
            delay = self.previous + 0.32 - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self.previous = time.monotonic()


class PacedTransport(httpx.BaseTransport):
    def __init__(self, gate):
        self.gate = gate
        self.transport = httpx.HTTPTransport()

    def handle_request(self, request):
        self.gate.wait()
        return self.transport.handle_request(request)

    def close(self):
        self.transport.close()


def collect(cohort, calendar: dict, archive_dir: Path) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (archive_dir / "collection.json").exists() and all(
        (archive_dir / f"{leg}-{m.symbol}.json").exists()
        for m in cohort.members
        for leg in ("native", "reality")
    ):
        return
    with BitgetMarketClient() as client:
        verified, raw = reverify_native_cohort(
            BitgetReferenceDataProvider(client),
            evidence_id=cohort.members[0].source_session_evidence_ids[0],
            original_universe_version=cohort.universe_version,
            expected_cohort_version=cohort.cohort_version,
        )
    if verified != cohort:
        raise NativeDataError("LIVE_COHORT_MISMATCH")
    write_json(archive_dir / "mapping.json", [asdict(r) for r in raw], private=True)
    print(json.dumps({"stage": "mappings", "verified": len(cohort.members)}), flush=True)
    gate = RequestGate()

    def native(member):
        path = archive_dir / f"native-{member.symbol}.json"
        if path.exists():
            return
        provider = AlpacaNativeEquityProvider(cohort, transport=PacedTransport(gate))
        began = time.monotonic()
        rows = []
        try:
            for s in calendar["sessions"]:
                row = {
                    "session": s,
                    "reality_symbol": member.symbol,
                    "native_ticker": member.native_ticker,
                }
                for leg, method in (
                    ("open", provider.get_session_open),
                    ("close", provider.get_session_close),
                ):
                    try:
                        target = method(member.symbol, target_date(s["session_date"]))
                        row[leg] = {
                            "status": target.status,
                            "history": encode_history(target.history),
                        }
                    except NativeDataError as exc:
                        structural = exc.code in {
                            "SESSION_BOUNDARY_LEAKAGE",
                            "DUPLICATE_TARGET",
                            "MALFORMED_BAR_PAYLOAD",
                            "DUPLICATE_OR_UNORDERED_TIMESTAMP",
                            "PAGINATION_NO_PROGRESS",
                            "PAGINATION_PAGE_LIMIT",
                        }
                        row[leg] = {
                            "status": "STRUCTURAL_FAILURE" if structural else "PROVIDER_FAILURE",
                            "error_code": exc.code,
                            "attempted_at": datetime.now(UTC).isoformat(),
                        }
                rows.append(row)
                # Checkpoints are private, never interpreted as complete symbol archives.
                write_json(archive_dir / f"checkpoint-{member.symbol}.json", rows, private=True)
                if len(rows) % 15 == 0:
                    print(
                        json.dumps(
                            {
                                "stage": "native",
                                "symbol": member.symbol,
                                "sessions_processed": len(rows),
                            }
                        ),
                        flush=True,
                    )
            write_json(
                path,
                {
                    "rows": rows,
                    "telemetry": provider.telemetry,
                    "request_attempts": provider.attempts,
                    "elapsed_seconds": round(time.monotonic() - began, 3),
                },
                private=True,
            )
            print(
                json.dumps(
                    {
                        "stage": "native_complete",
                        "symbol": member.symbol,
                        "sessions": len(rows),
                        "telemetry": provider.telemetry,
                    }
                ),
                flush=True,
            )
        finally:
            provider.close()

    def reality():
        with BitgetMarketClient() as client:
            for member in cohort.members:
                path = archive_dir / f"reality-{member.symbol}.json"
                if path.exists():
                    continue
                result = fetch_bounded_history(
                    client,
                    symbol=member.symbol,
                    interval="1H",
                    start=cohort.evaluation_start,
                    end=cohort.evaluation_end,
                    source_session_provider=CuratedBitgetSourceSessionProvider(),
                )
                write_json(
                    path,
                    {
                        "quality": result.quality.model_dump(mode="json"),
                        "observations": [
                            {
                                "candle": o.candle.model_dump(mode="json"),
                                "payload": o.payload,
                                "endpoint": o.endpoint,
                            }
                            for o in result.observations
                        ],
                    },
                    private=True,
                )
                print(
                    json.dumps(
                        {
                            "stage": "reality_complete",
                            "symbol": member.symbol,
                            "rows": len(result.observations),
                            "structural_quality": result.quality.structural_quality_status,
                        }
                    ),
                    flush=True,
                )
            write_json(
                archive_dir / "reality-telemetry.json",
                asdict(client.request_telemetry),
                private=True,
            )

    began = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        reality_job = pool.submit(reality)
        jobs = [pool.submit(native, m) for m in cohort.members[:3]]
        # Reserve three native workers even after the Reality worker finishes.
        remaining = iter(cohort.members[3:])
        while jobs:
            for job in list(jobs):
                if job.done():
                    job.result()
                    jobs.remove(job)
                    member = next(remaining, None)
                    if member is not None:
                        jobs.append(pool.submit(native, member))
            if jobs:
                time.sleep(0.1)
        reality_job.result()
    write_json(
        archive_dir / "collection.json",
        {
            "finished_at": datetime.now(UTC).isoformat(),
            "elapsed_seconds": round(time.monotonic() - began, 3),
            "native_workers": 3,
            "global_minimum_request_spacing_seconds": 0.32,
        },
        private=True,
    )
