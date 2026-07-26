from __future__ import annotations

import json

import pytest

from src import vast_api
from src.vast_api import VastApiClient, VastApiSchemaError


def test_schema_failure_always_persists_response(monkeypatch, tmp_path):
    diagnostic = tmp_path / "api_response.json"
    client = VastApiClient(
        "key",
        "https://example.invalid",
        1,
        diagnostic,
        revenue_endpoint="/machines/",
        auth_mode="query",
    )
    payload = {"unexpected": {"balance": 12.5}, "success": True}
    monkeypatch.setattr(client, "_get_json", lambda _endpoint: payload)

    with pytest.raises(VastApiSchemaError, match="lacks numeric"):
        client.get_account_balance()

    assert json.loads(diagnostic.read_text(encoding="utf-8")) == payload
    assert diagnostic.stat().st_mode & 0o777 == 0o600


def test_diagnostic_key_summary_does_not_include_values():
    payload = {"api_key": "must-not-appear", "revenue": {"daily": 1}}

    summary = VastApiClient._keys_for_diagnostic(payload)

    assert summary == ["api_key", "revenue"]
    assert "must-not-appear" not in str(summary)


def test_query_auth_passes_api_key_as_request_parameter(monkeypatch, tmp_path):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"balance": 4}

        def close(self):
            return None

    class Session:
        def __init__(self):
            self.headers = {}

        def mount(self, *_args, **_kwargs):
            return None

        def get(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr(vast_api.requests, "Session", Session)
    client = VastApiClient(
        "secret",
        "https://console.vast.ai/api/v0",
        5,
        tmp_path / "response.json",
        revenue_endpoint="/machines/",
        auth_mode="query",
    )

    client.get_account_balance()

    assert captured["url"] == "https://console.vast.ai/api/v0/machines/"
    assert captured["params"] == {"api_key": "secret"}
    assert "Authorization" not in client._session.headers


def test_current_user_balance_is_parsed(monkeypatch, tmp_path):
    client = VastApiClient(
        "secret",
        "https://console.vast.ai/api/v0",
        5,
        tmp_path / "response.json",
    )
    monkeypatch.setattr(
        client,
        "_get_json",
        lambda _endpoint: {"balance": 36.8099836823924, "paid_expected": 58945.27},
    )

    assert client.get_account_balance().amount_usd == 36.8099836823924


@pytest.mark.parametrize("invalid_balance", [None, "36.8", True])
def test_invalid_balance_type_is_rejected(monkeypatch, tmp_path, invalid_balance):
    client = VastApiClient(
        "secret", "https://console.vast.ai/api/v0", 5, tmp_path / "response.json"
    )
    monkeypatch.setattr(
        client, "_get_json", lambda _endpoint: {"balance": invalid_balance}
    )

    with pytest.raises(VastApiSchemaError, match="lacks numeric 'balance'"):
        client.get_account_balance()


def test_diagnostic_redacts_personal_and_secret_fields(tmp_path):
    client = VastApiClient("secret", "https://example.invalid", 5, tmp_path / "api.json")

    client._persist_diagnostic({
        "balance": 1.0,
        "email": "person@example.com",
        "rights": {"ssh_key": "private"},
    })

    saved = json.loads((tmp_path / "api.json").read_text(encoding="utf-8"))
    assert saved == {
        "balance": 1.0,
        "email": "[REDACTED]",
        "rights": {"ssh_key": "[REDACTED]"},
    }
