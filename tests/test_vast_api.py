from __future__ import annotations

import json

import pytest

from src.vast_api import VastApiClient, VastApiSchemaError


def test_schema_failure_always_persists_response(monkeypatch, tmp_path):
    diagnostic = tmp_path / "api_response.json"
    client = VastApiClient("key", "https://example.invalid", 1, diagnostic)
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
