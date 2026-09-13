from .client import BitgetMarketClient, CandleObservation, InstrumentDiscovery, PublicResponse
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
    "build_reality_universe_snapshot",
    "export_history",
    "fetch_bounded_history",
]
