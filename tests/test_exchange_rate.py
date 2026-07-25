from __future__ import annotations

from src.exchange_rate import ExchangeRateProvider


def test_exchange_rate_extracts_supported_provider_shapes(tmp_path):
    provider = ExchangeRateProvider(("https://example.invalid",), tmp_path / "rate.json", 1)

    assert provider._extract_jpy_rate({"rates": {"JPY": 150.0}}) == 150.0
    assert provider._extract_jpy_rate({"conversion_rates": {"JPY": 151.0}}) == 151.0
