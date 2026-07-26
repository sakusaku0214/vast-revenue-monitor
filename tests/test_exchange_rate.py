from __future__ import annotations

from src.exchange_rate import ExchangeRateProvider
from src.utils import read_json, write_json


def test_exchange_rate_extracts_supported_provider_shapes(tmp_path):
    provider = ExchangeRateProvider(("https://example.invalid",), tmp_path / "rate.json", 1)

    assert provider._extract_jpy_rate({"rates": {"JPY": 150.0}}) == 150.0
    assert provider._extract_jpy_rate({"conversion_rates": {"JPY": 151.0}}) == 151.0


def test_exchange_rate_fails_over_and_caches_provider(monkeypatch, tmp_path):
    path = tmp_path / "rate.json"
    provider = ExchangeRateProvider(("https://one", "https://two"), path, 1)

    def fetch(url):
        if url.endswith("one"):
            raise RuntimeError("provider unavailable")
        return 150.5

    monkeypatch.setattr(provider, "_fetch_rate", fetch)

    assert provider.get_usdjpy() == 150.5
    assert read_json(path, dict)["provider_url"] == "https://two"


def test_exchange_rate_uses_cache_after_all_providers_fail(monkeypatch, tmp_path):
    path = tmp_path / "rate.json"
    write_json(path, {"rate": 149.0})
    provider = ExchangeRateProvider(("https://one",), path, 1)
    monkeypatch.setattr(
        provider,
        "_fetch_rate",
        lambda _url: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    assert provider.get_usdjpy() == 149.0
