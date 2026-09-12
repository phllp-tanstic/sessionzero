from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class BitgetProviderError(Exception):
    kind: str
    message: str
    provider_code: str | None = None
    http_status: int | None = None
    retryable: bool = False
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.kind,
                "message": self.message,
                "provider": "bitget",
                "provider_code": self.provider_code,
                "retryable": self.retryable,
            }
        }
