from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sessionzero_bitget import BitgetMarketClient, BitgetProviderError
from sessionzero_bitget.capabilities import phase_zero_capabilities
from sessionzero_config import Settings, get_settings


def get_bitget_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[BitgetMarketClient]:
    with BitgetMarketClient(
        base_url=str(settings.bitget_base_url),
        timeout_seconds=settings.bitget_timeout_seconds,
        max_retries=settings.bitget_max_retries,
    ) as client:
        yield client


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    application = FastAPI(
        title="SessionZero API",
        version="0.1.0",
        docs_url="/docs" if resolved.environment != "production" else None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    @application.exception_handler(BitgetProviderError)
    async def provider_error_handler(_request: Request, exc: BitgetProviderError) -> JSONResponse:
        return JSONResponse(status_code=502, content=exc.as_dict())

    @application.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "sessionzero-api",
            "phase": "PHASE_0",
        }

    @application.get("/api/v1/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "source": "bitget_uta_v3",
            "capabilities": [item.model_dump(mode="json") for item in phase_zero_capabilities()],
        }

    @application.get("/api/v1/markets")
    def markets(
        client: Annotated[BitgetMarketClient, Depends(get_bitget_client)],
    ) -> dict[str, Any]:
        instruments = client.get_reality_instruments()
        return {
            "source": "bitget_uta_v3",
            "count": len(instruments),
            "markets": [item.model_dump(mode="json") for item in instruments],
        }

    return application


app = create_app()
