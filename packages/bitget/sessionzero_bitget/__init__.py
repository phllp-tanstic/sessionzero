from .client import (
    BitgetMarketClient,
    CandleObservation,
    InstrumentDiscovery,
    PublicResponse,
    RequestTelemetry,
)
from .coverage import (
    COVERAGE_TRANSFORMATION_VERSION,
    MINIMUM_OOS_DAYS,
    MINIMUM_TOTAL_HISTORY_DAYS,
    build_coverage_member,
    build_coverage_profile,
    coverage_status_for,
    profile_reality_coverage,
)
from .errors import BitgetProviderError
from .export import ExportResult, HistoryExportError, export_history
from .history import (
    BoundedHistoryResult,
    HistoryPaginationError,
    fetch_bounded_history,
)
from .reference import (
    BitgetReferenceDataProvider,
    RawReferenceResponse,
    ReferenceDataBundle,
)
from .universe import build_reality_universe_snapshot

__all__ = [
    "COVERAGE_TRANSFORMATION_VERSION",
    "MINIMUM_OOS_DAYS",
    "MINIMUM_TOTAL_HISTORY_DAYS",
    "BitgetMarketClient",
    "BitgetProviderError",
    "BitgetReferenceDataProvider",
    "BoundedHistoryResult",
    "CandleObservation",
    "ExportResult",
    "HistoryExportError",
    "HistoryPaginationError",
    "InstrumentDiscovery",
    "PublicResponse",
    "RawReferenceResponse",
    "ReferenceDataBundle",
    "RequestTelemetry",
    "build_coverage_member",
    "build_coverage_profile",
    "build_reality_universe_snapshot",
    "coverage_status_for",
    "export_history",
    "fetch_bounded_history",
    "profile_reality_coverage",
]
