from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sessionzero_config import get_settings
from sessionzero_database import create_database_engine
from sqlalchemy import Engine, text


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if value is None:
        pytest.skip("DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in value.rsplit("/", 1)[-1].split("?", 1)[0].lower():
        pytest.fail("PostgreSQL integration DATABASE_URL must name a database containing 'test'")
    return value


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    _database_url()
    get_settings.cache_clear()
    return Config("alembic.ini")


@pytest.fixture(scope="session")
def migrated_engine(alembic_config: Config) -> Iterator[Engine]:
    command.upgrade(alembic_config, "head")
    engine = create_database_engine(get_settings().require_database_url())
    yield engine
    engine.dispose()


@pytest.fixture
def database_engine(migrated_engine: Engine) -> Iterator[Engine]:
    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE decision_outcome_links, prospective_outcome_retrievals, "
                "prospective_outcome_versions, prospective_outcome_capture_runs, "
                "prospective_worker_runs, decision_time_snapshots, point_in_time_retrievals, "
                "point_in_time_observation_versions, point_in_time_capture_runs, "
                "phase1_dataset_manifests, historical_coverage_members, "
                "historical_coverage_profiles, "
                "historical_ingestion_manifest_entries, "
                "historical_ingestion_manifests, universe_discovery_observations, "
                "universe_snapshot_members, universe_snapshots, "
                "raw_reference_observations, reality_symbol_mappings, "
                "corporate_actions, share_capital_changes, suspension_records, "
                "source_session_metadata, raw_market_observations, normalized_market_candles, "
                "ingestion_runs RESTART IDENTITY CASCADE"
            )
        )
    yield migrated_engine
