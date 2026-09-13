from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime, timedelta

from sessionzero_bitget import (
    BitgetMarketClient,
    BitgetProviderError,
    build_reality_universe_snapshot,
)
from sessionzero_config import get_settings
from sqlalchemy.exc import SQLAlchemyError

from .engine import create_database_engine, verify_database_connection
from .universe import (
    ingest_manifest_subset,
    persist_historical_manifest,
    persist_universe_snapshot,
)


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include an offset")
    return parsed.astimezone(UTC)


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Persist a metadata-derived Reality universe and bounded history manifest"
    )
    parser.add_argument("--start", required=True, type=_utc)
    parser.add_argument("--end", required=True, type=_utc)
    parser.add_argument("--interval", default="1H")
    parser.add_argument("--subset-size", type=int, default=3)
    parser.add_argument("--page-limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--git-commit")
    args = parser.parse_args()
    if args.start >= args.end or args.end - args.start > timedelta(days=90):
        parser.error("range must be increasing and no longer than 90 days")
    settings = get_settings()
    engine = None
    try:
        engine = create_database_engine(settings.require_database_url())
        verify_database_connection(engine)
        with BitgetMarketClient(
            base_url=str(settings.bitget_base_url),
            timeout_seconds=settings.bitget_timeout_seconds,
            max_retries=settings.bitget_max_retries,
        ) as client:
            snapshot = build_reality_universe_snapshot(client, interval=args.interval)
            snapshot_result = persist_universe_snapshot(engine, snapshot)
            manifest = ingest_manifest_subset(
                engine,
                client,
                snapshot,
                start=args.start,
                end=args.end,
                subset_size=args.subset_size,
                git_commit=args.git_commit or _git_commit(),
                page_limit=args.page_limit,
                max_pages=args.max_pages,
            )
            manifest_written = persist_historical_manifest(engine, manifest)
        exclusions = Counter(
            reason.value for member in snapshot.members for reason in member.exclusion_reasons
        )
        output = {
            "verification_utc": snapshot.generated_at.isoformat(),
            "universe_version": snapshot.universe_version,
            "total_reality_instruments": len(snapshot.members),
            "eligible_count": sum(member.technically_eligible for member in snapshot.members),
            "ineligible_count": sum(not member.technically_eligible for member in snapshot.members),
            "mapping_coverage": sum(
                member.native_ticker is not None for member in snapshot.members
            ),
            "source_session_known_count": sum(
                member.source_session_status != "UNKNOWN" for member in snapshot.members
            ),
            "source_session_unknown_count": sum(
                member.source_session_status == "UNKNOWN" for member in snapshot.members
            ),
            "exclusion_counts": dict(sorted(exclusions.items())),
            "snapshot_persistence": {
                "snapshot_written": snapshot_result.snapshot_written,
                "members_written": snapshot_result.members_written,
                "observation_id": str(snapshot_result.observation_id),
            },
            "manifest": manifest.model_dump(mode="json"),
            "manifest_written": manifest_written,
        }
        print(json.dumps(output, indent=2, sort_keys=True))
    except (BitgetProviderError, SQLAlchemyError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": {"code": "UNIVERSE_MANIFEST_FAILED", "message": str(exc)}}))
        raise SystemExit(1) from exc
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
