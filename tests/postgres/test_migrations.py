from __future__ import annotations

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sessionzero_config import get_settings
from sessionzero_database import create_database_engine
from sqlalchemy import inspect, text

pytestmark = pytest.mark.postgres


def test_upgrade_downgrade_and_restore(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = create_database_engine(get_settings().require_database_url())
    try:
        assert set(inspect(engine).get_table_names()) >= {
            "alembic_version",
            "ingestion_runs",
            "raw_market_observations",
            "normalized_market_candles",
            "raw_reference_observations",
            "reality_symbol_mappings",
            "corporate_actions",
            "share_capital_changes",
            "suspension_records",
            "source_session_metadata",
            "universe_snapshots",
            "universe_discovery_observations",
            "universe_snapshot_members",
            "historical_ingestion_manifests",
            "historical_ingestion_manifest_entries",
            "historical_coverage_profiles",
            "historical_coverage_members",
        }
        manifest_columns = {
            column["name"]
            for column in inspect(engine).get_columns("historical_ingestion_manifest_entries")
        }
        assert "records_available_for_requested_window" in manifest_columns
        profile_columns = {
            column["name"] for column in inspect(engine).get_columns("historical_coverage_profiles")
        }
        assert {
            "evaluation_scope",
            "cohort_version",
            "cohort_derivation_version",
            "source_session_evidence_version",
            "git_commit",
        } <= profile_columns
        coverage_columns = {
            column["name"] for column in inspect(engine).get_columns("historical_coverage_members")
        }
        assert {
            "expected_open_interval_count",
            "source_session_unknown_interval_count",
            "holiday_ambiguous_timestamps",
            "observed_over_known_expected",
            "missing_over_known_expected",
            "unknown_fraction",
            "left_censored",
            "source_session_evidence_ids",
            "structural_quality_status",
            "provider_boundary_spillover_count",
            "meets_duration_requirement",
            "final_oos_window_start",
            "final_oos_window_end",
            "pre_oos_observation_present",
            "oos_observation_present",
            "final_oos_feasible",
        } <= coverage_columns
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                "20260914_07"
            )
        command.downgrade(alembic_config, "20260912_01")
        legacy_run_id = uuid.uuid4()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO ingestion_runs "
                    "(run_id, provider, operation, started_at, finished_at, status, "
                    "records_received, records_written) "
                    "VALUES (:run_id, 'legacy', 'history_candles', now(), now(), "
                    "'SUCCEEDED', 0, 0)"
                ),
                {"run_id": legacy_run_id},
            )
        command.upgrade(alembic_config, "head")
        with engine.connect() as connection:
            preserved = connection.execute(
                text(
                    "SELECT quality_status, pages_requested FROM ingestion_runs "
                    "WHERE run_id = :run_id"
                ),
                {"run_id": legacy_run_id},
            ).one()
        assert preserved.quality_status is None
        assert preserved.pages_requested is None
        command.downgrade(alembic_config, "base")
        assert set(inspect(engine).get_table_names()).isdisjoint(
            {"ingestion_runs", "raw_market_observations", "normalized_market_candles"}
        )
    finally:
        command.upgrade(alembic_config, "head")
        engine.dispose()
