from __future__ import annotations

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
        }
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                "20260912_01"
            )
        command.downgrade(alembic_config, "base")
        assert set(inspect(engine).get_table_names()).isdisjoint(
            {"ingestion_runs", "raw_market_observations", "normalized_market_candles"}
        )
    finally:
        command.upgrade(alembic_config, "head")
        engine.dispose()
