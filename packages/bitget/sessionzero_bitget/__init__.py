from .client import BitgetMarketClient, CandleObservation, PublicResponse
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

__all__ = [
    "BitgetMarketClient",
    "BitgetProviderError",
    "BitgetReferenceDataProvider",
    "BoundedHistoryResult",
    "CandleObservation",
    "ExportResult",
    "HistoryExportError",
    "HistoryPaginationError",
    "PublicResponse",
    "RawReferenceResponse",
    "ReferenceDataBundle",
    "export_history",
    "fetch_bounded_history",
]
