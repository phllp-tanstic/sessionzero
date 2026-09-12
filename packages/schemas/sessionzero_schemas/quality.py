from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class QualityStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class QualitySeverity(StrEnum):
    WARNING = "WARNING"
    ERROR = "ERROR"


class QualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    severity: QualitySeverity
    count: int = Field(ge=1)
    examples: tuple[str, ...] = ()


class CandleQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    interval: str
    requested_start: datetime
    requested_end: datetime
    observed_start: datetime | None
    observed_end: datetime | None
    page_count: int = Field(ge=0)
    records_received: int = Field(ge=0)
    records_unique: int = Field(ge=0)
    expected_candles: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    missing_examples: tuple[datetime, ...] = ()
    duplicate_count: int = Field(ge=0)
    out_of_order_count: int = Field(ge=0)
    unexpected_spacing_count: int = Field(ge=0)
    invalid_ohlc_count: int = Field(ge=0)
    non_positive_price_count: int = Field(ge=0)
    negative_volume_count: int = Field(ge=0)
    negative_turnover_count: int = Field(ge=0)
    outside_range_count: int = Field(ge=0)
    pagination_error_count: int = Field(ge=0)
    stale_pagination_count: int = Field(ge=0)
    empty_result: bool
    quality_status: QualityStatus
    issues: tuple[QualityIssue, ...] = ()
