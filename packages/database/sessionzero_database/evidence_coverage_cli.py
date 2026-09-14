from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from decimal import Decimal

from sessionzero_bitget import (
    BitgetMarketClient,
    derive_evidence_qualified_cohort,
    profile_reality_coverage,
)
from sessionzero_config import get_settings
from sessionzero_market_data import (
    CuratedBitgetSourceSessionProvider,
    load_bitget_source_session_evidence,
)
from sessionzero_schemas import CoverageEvaluationScope
from sqlalchemy.exc import SQLAlchemyError

from .coverage import load_accepted_universe, persist_historical_coverage_profile
from .engine import create_database_engine, verify_database_connection


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _ratio(numerator: int, denominator: int) -> Decimal | None:
    return None if denominator == 0 else Decimal(numerator) / denominator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the fixed-window evidence-qualified Reality coverage audit"
    )
    parser.add_argument("--universe-version", required=True)
    parser.add_argument("--page-limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--requests-per-second", type=float, default=10.0)
    args = parser.parse_args()
    if not 0 < args.requests_per_second <= 20:
        parser.error("requests-per-second must be greater than zero and no more than 20")

    settings = get_settings()
    engine = None
    try:
        engine = create_database_engine(settings.require_database_url())
        verify_database_connection(engine)
        universe = load_accepted_universe(engine, args.universe_version)
        evidence = load_bitget_source_session_evidence()
        cohort = derive_evidence_qualified_cohort(
            universe_version=universe.universe_version,
            universe_members=universe.members,
            evidence_dataset=evidence,
        )
        members_by_symbol = {member.reality_symbol: member for member in universe.members}
        cohort_members = tuple(members_by_symbol[item.symbol] for item in cohort.members)
        evidence_ids = {
            member.symbol: member.source_session_evidence_ids for member in cohort.members
        }
        git_commit = _git_commit()
        provider = CuratedBitgetSourceSessionProvider(
            evidence=evidence.evidence,
            transformation_version=evidence.transformation_version,
        )
        with BitgetMarketClient(
            base_url=str(settings.bitget_base_url),
            timeout_seconds=settings.bitget_timeout_seconds,
            max_retries=settings.bitget_max_retries,
            min_request_interval_seconds=1 / args.requests_per_second,
        ) as client:
            profile = profile_reality_coverage(
                client,
                universe_version=universe.universe_version,
                interval=cohort.interval,
                universe_members=cohort_members,
                evaluation_start=cohort.evaluation_start,
                evaluation_end=cohort.evaluation_end,
                subset_size=len(cohort.members),
                page_limit=args.page_limit,
                max_pages=args.max_pages,
                allow_full_universe=True,
                source_session_provider=provider,
                evaluation_scope=CoverageEvaluationScope.EVIDENCE_QUALIFIED_COHORT,
                cohort_version=cohort.cohort_version,
                cohort_derivation_version=cohort.derivation_version,
                source_session_evidence_version=cohort.source_session_evidence_version,
                git_commit=git_commit,
                source_session_evidence_ids=evidence_ids,
            )
        written = persist_historical_coverage_profile(engine, profile)
        statuses = Counter(member.coverage_status.value for member in profile.members)
        structural_statuses = Counter(
            None
            if member.structural_quality_status is None
            else member.structural_quality_status.value
            for member in profile.members
        )
        expected_open = sum(member.expected_open_interval_count for member in profile.members)
        observed_open = sum(
            member.observed_while_expected_open_count for member in profile.members
        )
        missing_open = sum(member.missing_while_expected_open for member in profile.members)
        unknown = sum(member.source_session_unknown_interval_count for member in profile.members)
        total_grid = sum(
            member.expected_open_interval_count
            + member.expected_closed_interval_count
            + member.source_session_unknown_interval_count
            for member in profile.members
        )
        output = {
            "cohort": cohort.model_dump(mode="json"),
            "profile": profile.model_dump(mode="json"),
            "profile_written": written,
            "aggregates": {
                "cohort_size": len(cohort.members),
                "coverage_status_counts": dict(sorted(statuses.items())),
                "structural_quality_status_counts": dict(
                    sorted((str(key), value) for key, value in structural_statuses.items())
                ),
                "sufficient_history_count": statuses.get(
                    "SUFFICIENT_MINIMUM_HISTORY", 0
                ),
                "expected_open_interval_count": expected_open,
                "observed_while_expected_open_count": observed_open,
                "missing_while_expected_open": missing_open,
                "source_session_unknown_interval_count": unknown,
                "holiday_ambiguous_interval_count": sum(
                    member.holiday_ambiguous_interval_count for member in profile.members
                ),
                "observed_over_known_expected": _ratio(observed_open, expected_open),
                "missing_over_known_expected": _ratio(missing_open, expected_open),
                "unknown_fraction": _ratio(unknown, total_grid),
                "left_censored_count": sum(member.left_censored for member in profile.members),
                "meets_duration_requirement_count": sum(
                    member.meets_duration_requirement for member in profile.members
                ),
                "final_oos_feasible_count": sum(
                    member.final_oos_feasible for member in profile.members
                ),
                "provider_boundary_spillover_count": sum(
                    member.provider_boundary_spillover_count for member in profile.members
                ),
                "request_count": sum(member.request_count for member in profile.members),
                "retry_count": sum(member.retry_count for member in profile.members),
                "rate_limit_count": sum(member.rate_limit_count for member in profile.members),
            },
        }
        print(json.dumps(output, indent=2, sort_keys=True, default=str))
    except (SQLAlchemyError, ValueError, subprocess.SubprocessError) as exc:
        error = {"error": {"code": "EVIDENCE_COVERAGE_AUDIT_FAILED", "message": str(exc)}}
        print(json.dumps(error))
        raise SystemExit(1) from exc
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
