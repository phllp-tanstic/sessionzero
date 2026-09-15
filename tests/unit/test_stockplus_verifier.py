from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).parents[2] / "scripts" / "verify_bitget_stockplus.py"
    spec = importlib.util.spec_from_file_location("verify_bitget_stockplus", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_signature_matches_documented_get_contract() -> None:
    module = _module()
    expected = base64.b64encode(
        hmac.new(
            b"secret",
            b"123GET/api/v3/stockplus/market/static?symbol=AAPL.US",
            hashlib.sha256,
        ).digest()
    ).decode()
    assert (
        module._signature("secret", "123", "/api/v3/stockplus/market/static", "symbol=AAPL.US")
        == expected
    )


def test_missing_credentials_fails_closed_without_network(monkeypatch, capsys) -> None:
    module = _module()
    for name in module.ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(module, "_get", lambda *_args: (_ for _ in ()).throw(AssertionError))
    assert module.main() == 2
    output = capsys.readouterr().out
    assert '"classification": "GATED"' in output
    assert '"requestsSent": 0' in output


def test_permission_error_classifies_as_gated() -> None:
    module = _module()
    assert module._classify({"code": "40006", "msg": "Invalid ACCESS_KEY"}) == "GATED"
