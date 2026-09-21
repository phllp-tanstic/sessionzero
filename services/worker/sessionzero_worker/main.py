"""Calendar-derived one-shot orchestration for remote prospective captures."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sessionzero_config import get_settings
from sessionzero_database.capture_cli import capture_iteration, git_commit
from sessionzero_database.dataset_artifacts import load_cohort
from sessionzero_database.engine import create_database_engine, verify_database_connection
from sessionzero_database.models import (
    DecisionOutcomeLink,
    DecisionTimeSnapshotRow,
    ProspectiveWorkerRun,
)
from sessionzero_database.outcome import OUTCOME_AVAILABILITY_DELAY, capture_outcome_iteration
from sessionzero_market_data import XnysTradingCalendar
from sessionzero_market_data.calendar import NEW_YORK
from sessionzero_schemas import WorkerRunStatus
from sqlalchemy import Engine, distinct, func, insert, select, text
from sqlalchemy.exc import SQLAlchemyError

DECISION_LEAD = timedelta(minutes=15)
EXPECTED_SYMBOLS = 21


def _utc_now() -> datetime:
    return datetime.now(UTC)


Clock = Callable[[], datetime]


@dataclass(frozen=True)
class SchedulePlan:
    action: str
    decision_timestamp: datetime | None
    scheduled_event_timestamp: datetime | None
    reason: str


def derive_schedule(now: datetime, calendar: XnysTradingCalendar) -> SchedulePlan:
    now = now.astimezone(UTC)
    local_date = now.astimezone(NEW_YORK).date()
    try:
        session = calendar.session_on(local_date)
    except ValueError:
        return SchedulePlan("SKIP", None, None, "NO_XNYS_SESSION")
    decision = session.regular_open - timedelta(hours=1)
    outcome_ready = session.regular_open + OUTCOME_AVAILABILITY_DELAY
    if now < decision - DECISION_LEAD:
        return SchedulePlan("SKIP", decision, decision, "BEFORE_DECISION_WINDOW")
    if now <= decision:
        return SchedulePlan("DECISION", decision, decision, "DECISION_WINDOW")
    if now < outcome_ready:
        return SchedulePlan("WAIT_OUTCOME", decision, outcome_ready, "OUTCOME_NOT_YET_AVAILABLE")
    return SchedulePlan("OUTCOME", decision, outcome_ready, "OUTCOME_AVAILABLE")


def _safe_log(event: str, **fields: object) -> None:
    allowed = {
        "event",
        "operation",
        "status",
        "decision_timestamp",
        "scheduled_event_timestamp",
        "actual_start_time",
        "completed_at",
        "symbols_expected",
        "symbols_captured",
        "snapshot_version",
        "outcome_links",
        "error_code",
        "reason",
    }
    record = {"event": event}
    record.update({key: value for key, value in fields.items() if key in allowed})
    print(json.dumps(record, sort_keys=True, default=str), flush=True)


def _snapshot_state(engine: Engine, decision: datetime) -> tuple[str | None, str | None, int]:
    with engine.connect() as connection:
        snapshot = connection.execute(
            select(
                DecisionTimeSnapshotRow.snapshot_version,
                DecisionTimeSnapshotRow.mapping_version,
            ).where(DecisionTimeSnapshotRow.decision_timestamp == decision)
        ).one_or_none()
        if snapshot is None:
            return None, None, 0
        links = connection.scalar(
            select(func.count(distinct(DecisionOutcomeLink.reality_symbol))).where(
                DecisionOutcomeLink.snapshot_version == snapshot.snapshot_version
            )
        )
        return snapshot.snapshot_version, snapshot.mapping_version, int(links or 0)


def _record(
    engine: Engine,
    *,
    operation: str,
    plan: SchedulePlan,
    started: datetime,
    status: WorkerRunStatus,
    commit: str,
    symbols_captured: int = 0,
    snapshot_version: str | None = None,
    outcome_links: int = 0,
    error_code: str | None = None,
    identity: tuple[str, str, str] | None = None,
    clock: Clock | None = None,
) -> dict[str, object]:
    clock = clock or _utc_now
    completed = max(clock(), started)
    scheduled = plan.scheduled_event_timestamp
    lateness = (
        max(Decimal(0), Decimal(str((started - scheduled).total_seconds()))) if scheduled else None
    )
    universe, cohort, mapping = identity or (None, None, None)
    worker_run_id = uuid.uuid4()
    degraded = status in {WorkerRunStatus.PARTIAL, WorkerRunStatus.PROVIDER_UNAVAILABLE}
    provider_status = {
        "bitget": ("DEGRADED" if degraded else "USED") if operation == "DECISION" else "NOT_USED",
        "alpaca": ("DEGRADED" if degraded else "USED")
        if operation in {"DECISION", "OUTCOME"}
        else "NOT_USED",
    }
    with engine.begin() as connection:
        connection.execute(
            insert(ProspectiveWorkerRun).values(
                worker_run_id=worker_run_id,
                operation=operation,
                decision_timestamp=plan.decision_timestamp,
                scheduled_event_timestamp=scheduled,
                actual_start_time=started,
                completed_at=completed,
                lateness_seconds=lateness,
                status=status.value,
                symbols_expected=EXPECTED_SYMBOLS if plan.decision_timestamp else 0,
                symbols_captured=symbols_captured,
                provider_status=provider_status,
                snapshot_version=snapshot_version,
                outcome_links=outcome_links,
                error_code=error_code,
                git_commit=commit,
                universe_version=universe,
                cohort_version=cohort,
                mapping_version=mapping,
            )
        )
    result = {
        "worker_run_id": str(worker_run_id),
        "operation": operation,
        "status": status.value,
        "decision_timestamp": plan.decision_timestamp.isoformat()
        if plan.decision_timestamp
        else None,
        "scheduled_event_timestamp": scheduled.isoformat() if scheduled else None,
        "actual_start_time": started.isoformat(),
        "completed_at": completed.isoformat(),
        "symbols_expected": EXPECTED_SYMBOLS if plan.decision_timestamp else 0,
        "symbols_captured": symbols_captured,
        "snapshot_version": snapshot_version,
        "outcome_links": outcome_links,
        "error_code": error_code,
    }
    _safe_log("prospective_worker_run", **result)
    return result


def run_tick(
    *,
    now: datetime | None = None,
    engine: Engine | None = None,
    calendar: XnysTradingCalendar | None = None,
    decision_runner: Callable[..., dict] = capture_iteration,
    outcome_runner: Callable[..., dict] = capture_outcome_iteration,
    commit: str | None = None,
    clock: Clock | None = None,
) -> dict[str, object]:
    clock = clock or (lambda: now if now is not None else _utc_now())
    started = (now or clock()).astimezone(UTC)
    owned_engine = engine is None
    try:
        engine = engine or create_database_engine(get_settings().require_database_url())
        verify_database_connection(engine)
    except Exception:
        result = {
            "operation": "TICK",
            "status": WorkerRunStatus.DATABASE_FAILURE.value,
            "actual_start_time": started.isoformat(),
            "error_code": "DATABASE_UNAVAILABLE",
        }
        _safe_log("prospective_worker_run", **result)
        return result

    calendar = calendar or XnysTradingCalendar()
    commit = commit or git_commit()
    plan = derive_schedule(started, calendar)
    try:
        try:
            cohort = load_cohort()
            if len(cohort.members) != EXPECTED_SYMBOLS:
                raise ValueError("accepted cohort size mismatch")
            identity = (cohort.universe_version, cohort.cohort_version, cohort.cohort_version)
        except Exception:
            return _record(
                engine,
                operation="TICK",
                plan=plan,
                started=started,
                clock=clock,
                status=WorkerRunStatus.IDENTITY_MISMATCH,
                commit=commit,
                error_code="COHORT_IDENTITY_MISMATCH",
            )

        if plan.decision_timestamp is None:
            return _record(
                engine,
                operation="TICK",
                plan=plan,
                started=started,
                clock=clock,
                status=WorkerRunStatus.SKIPPED_NO_ACTION,
                commit=commit,
                error_code=plan.reason,
                identity=identity,
            )
        snapshot, snapshot_mapping, links = _snapshot_state(engine, plan.decision_timestamp)
        if snapshot is not None and snapshot_mapping != cohort.cohort_version:
            return _record(
                engine,
                operation="TICK",
                plan=plan,
                started=started,
                clock=clock,
                status=WorkerRunStatus.IDENTITY_MISMATCH,
                commit=commit,
                snapshot_version=snapshot,
                error_code="SNAPSHOT_MAPPING_MISMATCH",
                identity=identity,
            )
        symbols = tuple(member.symbol for member in cohort.members)
        if plan.action == "DECISION":
            if snapshot is not None:
                return _record(
                    engine,
                    operation="DECISION",
                    plan=plan,
                    started=started,
                    status=WorkerRunStatus.SUCCEEDED,
                    commit=commit,
                    symbols_captured=EXPECTED_SYMBOLS,
                    snapshot_version=snapshot,
                    outcome_links=links,
                    identity=identity,
                )
            if clock() > plan.decision_timestamp:
                return _record(
                    engine,
                    operation="DECISION",
                    plan=plan,
                    started=started,
                    status=WorkerRunStatus.MISSED_DECISION_WINDOW,
                    commit=commit,
                    error_code="WORKER_STARTED_AFTER_DECISION",
                    identity=identity,
                )
            try:
                result = decision_runner(
                    decision_timestamp=plan.decision_timestamp,
                    symbols=symbols,
                    lead_minutes=int(DECISION_LEAD.total_seconds() / 60),
                )
                return _record(
                    engine,
                    operation="DECISION",
                    plan=plan,
                    started=started,
                    status=WorkerRunStatus.SUCCEEDED,
                    commit=commit,
                    symbols_captured=EXPECTED_SYMBOLS,
                    snapshot_version=str(result["snapshot_version"]),
                    identity=identity,
                )
            except SQLAlchemyError:
                status, code = WorkerRunStatus.DATABASE_FAILURE, "DECISION_DATABASE_FAILURE"
            except Exception as exc:
                captured = int(getattr(exc, "completed_symbols", 0))
                if captured:
                    status = WorkerRunStatus.PARTIAL
                else:
                    status = WorkerRunStatus.PROVIDER_UNAVAILABLE
                return _record(
                    engine,
                    operation="DECISION",
                    plan=plan,
                    started=started,
                    status=status,
                    commit=commit,
                    symbols_captured=captured,
                    error_code="DECISION_PROVIDER_FAILURE",
                    identity=identity,
                )
            return _record(
                engine,
                operation="DECISION",
                plan=plan,
                started=started,
                clock=clock,
                status=status,
                commit=commit,
                error_code=code,
                identity=identity,
            )

        if snapshot is None:
            return _record(
                engine,
                operation="DECISION",
                plan=plan,
                started=started,
                clock=clock,
                status=WorkerRunStatus.MISSED_DECISION_WINDOW,
                commit=commit,
                error_code="NO_SNAPSHOT_AT_DECISION",
                identity=identity,
            )
        if plan.action == "WAIT_OUTCOME" or links == EXPECTED_SYMBOLS:
            return _record(
                engine,
                operation="TICK" if plan.action == "WAIT_OUTCOME" else "OUTCOME",
                plan=plan,
                started=started,
                clock=clock,
                status=WorkerRunStatus.SKIPPED_NO_ACTION
                if plan.action == "WAIT_OUTCOME"
                else WorkerRunStatus.SUCCEEDED,
                commit=commit,
                symbols_captured=EXPECTED_SYMBOLS if links == EXPECTED_SYMBOLS else 0,
                snapshot_version=snapshot,
                outcome_links=links,
                error_code=plan.reason if plan.action == "WAIT_OUTCOME" else None,
                identity=identity,
            )
        try:
            result = outcome_runner(decision_timestamp=plan.decision_timestamp)
            new_links = int(result["outcome_links_written"])
            return _record(
                engine,
                operation="OUTCOME",
                plan=plan,
                started=started,
                clock=clock,
                status=WorkerRunStatus.SUCCEEDED,
                commit=commit,
                symbols_captured=EXPECTED_SYMBOLS,
                snapshot_version=snapshot,
                outcome_links=links + new_links,
                identity=identity,
            )
        except SQLAlchemyError:
            status, code = WorkerRunStatus.DATABASE_FAILURE, "OUTCOME_DATABASE_FAILURE"
        except Exception as exc:
            captured = int(getattr(exc, "completed_symbols", 0))
            status = WorkerRunStatus.PARTIAL if captured else WorkerRunStatus.PROVIDER_UNAVAILABLE
            return _record(
                engine,
                operation="OUTCOME",
                plan=plan,
                started=started,
                clock=clock,
                status=status,
                commit=commit,
                symbols_captured=captured,
                snapshot_version=snapshot,
                outcome_links=links,
                error_code="OUTCOME_PROVIDER_FAILURE",
                identity=identity,
            )
        return _record(
            engine,
            operation="OUTCOME",
            plan=plan,
            started=started,
            status=status,
            commit=commit,
            snapshot_version=snapshot,
            outcome_links=links,
            error_code=code,
            identity=identity,
        )
    except SQLAlchemyError:
        result = {
            "operation": "TICK",
            "status": WorkerRunStatus.DATABASE_FAILURE.value,
            "actual_start_time": started.isoformat(),
            "error_code": "WORKER_DATABASE_FAILURE",
        }
        _safe_log("prospective_worker_run", **result)
        return result
    finally:
        if owned_engine:
            engine.dispose()


def worker_status(engine: Engine | None = None) -> dict[str, object]:
    owned_engine = engine is None
    engine = engine or create_database_engine(get_settings().require_database_url())
    try:
        verify_database_connection(engine)
        with engine.connect() as connection:
            migration_head = connection.scalar(text("SELECT version_num FROM alembic_version"))
            latest_run = (
                connection.execute(
                    select(ProspectiveWorkerRun)
                    .order_by(ProspectiveWorkerRun.actual_start_time.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
            latest_snapshot = (
                connection.execute(
                    select(DecisionTimeSnapshotRow)
                    .order_by(DecisionTimeSnapshotRow.decision_timestamp.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
            links = 0
            if latest_snapshot:
                links = int(
                    connection.scalar(
                        select(func.count(distinct(DecisionOutcomeLink.reality_symbol))).where(
                            DecisionOutcomeLink.snapshot_version
                            == latest_snapshot["snapshot_version"]
                        )
                    )
                    or 0
                )
        return {
            "database": "AVAILABLE",
            "migration_head": migration_head,
            "last_run": {
                "status": latest_run["status"],
                "operation": latest_run["operation"],
                "actual_start_time": latest_run["actual_start_time"].isoformat(),
                "decision_timestamp": latest_run["decision_timestamp"].isoformat()
                if latest_run["decision_timestamp"]
                else None,
                "symbols_captured": latest_run["symbols_captured"],
                "provider_status": latest_run["provider_status"],
                "lateness_seconds": str(latest_run["lateness_seconds"])
                if latest_run["lateness_seconds"] is not None
                else None,
                "stale": datetime.now(UTC) - latest_run["actual_start_time"]
                > timedelta(minutes=20),
            }
            if latest_run
            else None,
            "latest_snapshot": latest_snapshot["snapshot_version"] if latest_snapshot else None,
            "latest_decision_timestamp": latest_snapshot["decision_timestamp"].isoformat()
            if latest_snapshot
            else None,
            "latest_outcome_links": links,
            "outcome_complete": links == EXPECTED_SYMBOLS,
        }
    finally:
        if owned_engine:
            engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("tick", "status"), nargs="?", default="tick")
    args = parser.parse_args()
    result = run_tick() if args.command == "tick" else worker_status()
    print(json.dumps(result, sort_keys=True, default=str))
    if result.get("status") in {
        WorkerRunStatus.FAILED.value,
        WorkerRunStatus.PARTIAL.value,
        WorkerRunStatus.PROVIDER_UNAVAILABLE.value,
        WorkerRunStatus.DATABASE_FAILURE.value,
        WorkerRunStatus.IDENTITY_MISMATCH.value,
    }:
        sys.exit(1)


if __name__ == "__main__":
    main()
