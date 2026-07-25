"""USD/JPY exchange-rate retrieval with provider failover and cache fallback."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils import read_json, write_json

LOGGER = logging.getLogger(__name__)


class ExchangeRateProvider:
    """Fetch live USDJPY rates from multiple providers with cache fallback."""

    def __init__(self, urls: tuple[str, ...], cache_path: Path, timeout_seconds: int) -> None:
        if not urls:
            raise ValueError("At least one exchange-rate API URL is required")
        self._urls = urls
        self._cache_path = cache_path
        self._timeout = timeout_seconds
        self._session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retry))
        self._session.mount("http://", HTTPAdapter(max_retries=retry))

    def get_usdjpy(self) -> float:
        """Return a live rate, or the last cached rate if every provider fails."""
        failures: list[str] = []
        for url in self._urls:
            try:
                rate = self._fetch_rate(url)
                self._write_cache(rate, url)
                return rate
            except Exception as exc:  # noqa: BLE001 - failover boundary
                failures.append(f"{url}: {exc}")
                LOGGER.warning("Exchange API failed for %s: %s", url, exc)
        return self._cached_rate(failures)

    def _fetch_rate(self, url: str) -> float:
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        payload = response.json()
        rate = self._extract_jpy_rate(payload)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("USDJPY rate must be positive")
        return rate

    @staticmethod
    def _extract_jpy_rate(payload: Any) -> float:
        if not isinstance(payload, dict):
            raise ValueError("Exchange response was not a JSON object")
        rates = payload.get("rates")
        if isinstance(rates, dict) and "JPY" in rates:
            return float(rates["JPY"])
        conversion_rates = payload.get("conversion_rates")
        if isinstance(conversion_rates, dict) and "JPY" in conversion_rates:
            return float(conversion_rates["JPY"])
        raise KeyError("Exchange response did not include a JPY rate")

    def _write_cache(self, rate: float, provider_url: str) -> None:
        write_json(
            self._cache_path,
            {
                "rate": rate,
                "provider_url": provider_url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _cached_rate(self, failures: list[str]) -> float:
        LOGGER.warning("All exchange APIs failed; using cached USDJPY if available")
        cached = read_json(self._cache_path, lambda: {"rate": 0.0, "timestamp": None})
        rate = float(cached.get("rate", 0.0))
        if not math.isfinite(rate) or rate <= 0:
            details = "; ".join(failures)
            raise RuntimeError(f"No valid cached exchange rate is available: {details}")
        return rate
