"""USD/JPY exchange-rate retrieval with persistent fallback cache."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils import read_json, write_json

LOGGER = logging.getLogger(__name__)


class ExchangeRateProvider:
    """Fetch live USDJPY rates and cache the last successful value."""

    def __init__(self, url: str, cache_path: Path, timeout_seconds: int) -> None:
        self._url = url
        self._cache_path = cache_path
        self._timeout = timeout_seconds
        self._session = requests.Session()
        retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
        self._session.mount("https://", HTTPAdapter(max_retries=retry))
        self._session.mount("http://", HTTPAdapter(max_retries=retry))

    def get_usdjpy(self) -> float:
        """Return a live rate, or the last cached rate if the provider fails."""
        try:
            response = self._session.get(self._url, timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
            rate = float(payload["rates"]["JPY"])
            write_json(
                self._cache_path,
                {"rate": rate, "timestamp": datetime.now(timezone.utc).isoformat()},
            )
            return rate
        except Exception as exc:  # noqa: BLE001 - fallback cache is intentional boundary
            LOGGER.warning("Exchange API failed; using cached USDJPY if available: %s", exc)
            cached = read_json(self._cache_path, lambda: {"rate": 0.0, "timestamp": None})
            rate = float(cached.get("rate", 0.0))
            if rate <= 0:
                raise RuntimeError("No valid cached exchange rate is available") from exc
            return rate
