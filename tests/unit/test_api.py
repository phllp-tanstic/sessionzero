from collections.abc import Iterator

from fastapi.testclient import TestClient
from sessionzero_api.main import create_app, get_bitget_client
from sessionzero_bitget.errors import BitgetProviderError
from sessionzero_config import Settings
from sessionzero_schemas import MarketInstrument


class StubClient:
    def get_reality_instruments(self) -> list[MarketInstrument]:
        return []


def test_health_and_capabilities() -> None:
    client = TestClient(create_app(Settings(environment="test")))
    assert client.get("/health").json()["phase"] == "PHASE_0"
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    assert len(response.json()["capabilities"]) == 6


def test_markets_has_no_fixture_fallback_on_provider_failure() -> None:
    app = create_app(Settings(environment="test"))

    def fail() -> Iterator[StubClient]:
        raise BitgetProviderError(
            kind="UPSTREAM_NETWORK_ERROR", message="provider unavailable", retryable=True
        )
        yield StubClient()

    app.dependency_overrides[get_bitget_client] = fail
    response = TestClient(app, raise_server_exceptions=False).get("/api/v1/markets")
    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "UPSTREAM_NETWORK_ERROR",
            "message": "provider unavailable",
            "provider": "bitget",
            "provider_code": None,
            "retryable": True,
        }
    }
    assert "markets" not in response.json()
