from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from statistics import median

from sessionzero_bitget import BitgetMarketClient, profile_reality_coverage
from sessionzero_config import get_settings
from sqlalchemy.exc import SQLAlchemyError

from .coverage import load_accepted_universe, persist_historical_coverage_profile
from .engine import create_database_engine, verify_database_connection


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include an offset")
    return parsed.astimezone(UTC)


def _duration_distribution(values: list[float]) -> dict[str, int]:
    return {
        "under_30_days": sum(value < 30 for value in values),
        "30_to_under_60_days": sum(30 <= value < 60 for value in values),
        "60_to_under_90_days": sum(60 <= value < 90 for value in values),
        "90_days_or_more": sum(value >= 90 for value in values),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile Reality historical coverage from an accepted universe snapshot"
    )
    parser.add_argument("--universe-version", required=True)
    parser.add_argument("--end", required=True, type=_utc)
    parser.add_argument("--evaluation-days", type=int, default=90)
    parser.add_argument("--subset-size", type=int, default=10)
    parser.add_argument("--full-universe", action="store_true")
    parser.add_argument("--page-limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--requests-per-second", type=float, default=10.0)
    args = parser.parse_args()
    if not 60 <= args.evaluation_days <= 90:
        parser.error("evaluation-days must be between 60 and 90")
    if not 0 < args.requests_per_second <= 20:
        parser.error("requests-per-second must be greater than zero and no more than 20")

    settings = get_settings()
    engine = None
    try:
        engine = create_database_engine(settings.require_database_url())
        verify_database_connection(engine)
        universe = load_accepted_universe(engine, args.universe_version)
        eligible_count = sum(member.technically_eligible for member in universe.members)
        subset_size = eligible_count if args.full_universe else args.subset_size
        evaluation_start = args.end - timedelta(days=args.evaluation_days)
        with BitgetMarketClient(
            base_url=str(settings.bitget_base_url),
            timeout_seconds=settings.bitget_timeout_seconds,
            max_retries=settings.bitget_max_retries,
            min_request_interval_seconds=1 / args.requests_per_second,
        ) as client:
            profile = profile_reality_coverage(
                client,
                universe_version=universe.universe_version,
                interval=universe.interval,
                universe_members=universe.members,
                evaluation_start=evaluation_start,
                evaluation_end=args.end,
                subset_size=subset_size,
                page_limit=args.page_limit,
                max_pages=args.max_pages,
                allow_full_universe=args.full_universe,
            )
        written = persist_historical_coverage_profile(engine, profile)
        statuses = Counter(member.coverage_status.value for member in profile.members)
        durations = [member.observed_duration_days for member in profile.members]
        output = {
            "profile": profile.model_dump(mode="json"),
            "profile_written": written,
            "summary": {
                "total_symbols_in_universe": len(universe.members),
                "eligible_symbols_in_universe": eligible_count,
                "profiled_symbols": len(profile.members),
                "coverage_status_counts": dict(sorted(statuses.items())),
                "rate_limited": sum(member.rate_limit_count for member in profile.members),
                "retried": sum(member.retry_count for member in profile.members),
                "request_count": sum(member.request_count for member in profile.members),
                "duration_distribution": _duration_distribution(durations),
                "median_observed_duration_days": median(durations),
                "minimum_observed_duration_days": min(durations),
                "maximum_observed_duration_days": max(durations),
                "maximum_request_budget": subset_size * args.max_pages,
                "rate_limit_floor_seconds_for_maximum_request_budget": (
                    subset_size * args.max_pages / args.requests_per_second
                ),
            },
        }
        print(json.dumps(output, indent=2, sort_keys=True))
    except (SQLAlchemyError, ValueError) as exc:
        print(json.dumps({"error": {"code": "COVERAGE_PROFILE_FAILED", "message": str(exc)}}))
        raise SystemExit(1) from exc
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
