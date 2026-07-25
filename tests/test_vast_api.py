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

    with pytest.raises(VastApiSchemaError, match="top-level keys"):
        client.get_revenue_snapshot()

    assert json.loads(diagnostic.read_text(encoding="utf-8")) == payload
    assert diagnostic.stat().st_mode & 0o777 == 0o600


def test_diagnostic_key_summary_does_not_include_values():
    payload = {"api_key": "must-not-appear", "revenue": {"daily": 1}}

    summary = VastApiClient._keys_for_diagnostic(payload)

    assert summary == ["api_key", "revenue"]
    assert "must-not-appear" not in str(summary)


def test_machine_revenue_is_aggregated_and_missing_host_values_count_as_zero():
    machines = [
        {
            "revenue": {
                "hourly": 1,
                "daily": 2,
                "weekly": 3,
                "monthly": 4,
            }
        },
        {"machine_id": 2},
        {
            "earnings": {
                "hourly_revenue": 10,
                "daily_revenue": 20,
                "weekly_revenue": 30,
                "monthly_revenue": 40,
            }
        },
    ]

    assert VastApiClient._sum_machine_revenue(machines) == {
        "hourly": 11,
        "daily": 22,
        "weekly": 33,
        "monthly": 44,
    }


def test_query_auth_passes_api_key_as_request_parameter(monkeypatch, tmp_path):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"hourly": 1, "daily": 2, "weekly": 3, "monthly": 4}

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

    client.get_revenue_snapshot()

    assert captured["url"] == "https://console.vast.ai/api/v0/machines/"
    assert captured["params"] == {"api_key": "secret"}
    assert "Authorization" not in client._session.headers
