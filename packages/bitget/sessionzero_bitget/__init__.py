from .client import BitgetMarketClient, CandleObservation
from .errors import BitgetProviderError
from .export import ExportResult, HistoryExportError, export_history
from .history import (
    BoundedHistoryResult,
    HistoryPaginationError,
    fetch_bounded_history,
)

__all__ = [
    "BitgetMarketClient",
    "BitgetProviderError",
    "BoundedHistoryResult",
    "CandleObservation",
    "ExportResult",
    "HistoryExportError",
    "HistoryPaginationError",
    "export_history",
    "fetch_bounded_history",
]
