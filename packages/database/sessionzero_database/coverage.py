from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sessionzero_schemas import (
    HistoricalCoverageProfile,
    UniverseEligibilityReason,
    UniverseMappingStatus,
    UniverseMember,
)
from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from .models import (
    HistoricalCoverageMemberRow,
    HistoricalCoverageProfileRow,
    UniverseSnapshotMemberRow,
    UniverseSnapshotRow,
)


@dataclass(frozen=True, slots=True)
class AcceptedUniverse:
    universe_version: str
    interval: str
    members: tuple[UniverseMember, ...]


def load_accepted_universe(engine: Engine, universe_version: str) -> AcceptedUniverse:
    with engine.connect() as connection:
        snapshot = (
            connection.execute(
                select(UniverseSnapshotRow.universe_version, UniverseSnapshotRow.interval).where(
                    UniverseSnapshotRow.universe_version == universe_version
                )
            )
            .mappings()
            .one_or_none()
        )
        if snapshot is None:
            raise ValueError("accepted universe_version was not found")
        rows = connection.execute(
            select(
                UniverseSnapshotMemberRow.reality_symbol,
                UniverseSnapshotMemberRow.base_coin,
                UniverseSnapshotMemberRow.quote_coin,
                UniverseSnapshotMemberRow.native_ticker,
                UniverseSnapshotMemberRow.instrument_status,
                UniverseSnapshotMemberRow.is_reality,
                UniverseSnapshotMemberRow.launch_time,
                UniverseSnapshotMemberRow.price_precision,
                UniverseSnapshotMemberRow.quantity_precision,
                UniverseSnapshotMemberRow.trading_periods,
                UniverseSnapshotMemberRow.weekend_tradable,
                UniverseSnapshotMemberRow.mapping_status,
                UniverseSnapshotMemberRow.source_session_status,
                UniverseSnapshotMemberRow.source_session_mode,
                UniverseSnapshotMemberRow.technically_eligible,
                UniverseSnapshotMemberRow.exclusion_reasons,
                UniverseSnapshotMemberRow.raw_metadata_key,
            )
            .where(UniverseSnapshotMemberRow.universe_version == universe_version)
            .order_by(UniverseSnapshotMemberRow.reality_symbol)
        ).mappings()
        members = tuple(
            UniverseMember(
                reality_symbol=row.reality_symbol,
                base_coin=row.base_coin,
                quote_coin=row.quote_coin,
                native_ticker=row.native_ticker,
                instrument_status=row.instrument_status,
                is_reality=row.is_reality,
                launch_time=row.launch_time,
                price_precision=row.price_precision,
                quantity_precision=row.quantity_precision,
                trading_periods=tuple(row.trading_periods),
                weekend_tradable=row.weekend_tradable,
                mapping_status=UniverseMappingStatus(row.mapping_status),
                source_session_status=row.source_session_status,
                source_session_mode=row.source_session_mode,
                technically_eligible=row.technically_eligible,
                exclusion_reasons=tuple(
                    UniverseEligibilityReason(value) for value in row.exclusion_reasons
                ),
                raw_metadata_key=row.raw_metadata_key,
            )
            for row in rows
        )
    if not members:
        raise ValueError("accepted universe snapshot has no members")
    return AcceptedUniverse(snapshot.universe_version, snapshot.interval, members)


def persist_historical_coverage_profile(engine: Engine, profile: HistoricalCoverageProfile) -> bool:
    with engine.begin() as connection:
        root = connection.execute(
            postgresql_insert(HistoricalCoverageProfileRow)
            .values(
                profile_version=profile.profile_version,
                universe_version=profile.universe_version,
                interval=profile.interval,
                transformation_version=profile.transformation_version,
                evaluation_start=profile.evaluation_start,
                evaluation_end=profile.evaluation_end,
                generated_at=profile.generated_at,
                evaluation_scope=profile.evaluation_scope.value,
                cohort_version=profile.cohort_version,
                cohort_derivation_version=profile.cohort_derivation_version,
                source_session_evidence_version=profile.source_session_evidence_version,
                git_commit=profile.git_commit,
                minimum_total_history_days=profile.minimum_total_history_days,
                minimum_oos_days=profile.minimum_oos_days,
            )
            .on_conflict_do_nothing(index_elements=["profile_version"])
            .returning(HistoricalCoverageProfileRow.profile_version)
        )
        written = root.scalar_one_or_none() is not None
        if written:
            connection.execute(
                postgresql_insert(HistoricalCoverageMemberRow).values(
                    [
                        {
                            "profile_version": profile.profile_version,
                            **member.model_dump(mode="python", exclude={"coverage_status"}),
                            "holiday_ambiguous_timestamps": [
                                value.isoformat() for value in member.holiday_ambiguous_timestamps
                            ],
                            "observed_duration_days": Decimal(
                                f"{member.observed_duration_days:.6f}"
                            ),
                            "coverage_status": member.coverage_status.value,
                        }
                        for member in profile.members
                    ]
                )
            )
    return written
