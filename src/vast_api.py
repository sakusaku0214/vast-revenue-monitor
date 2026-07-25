"""Vast.ai API client."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import RevenueSnapshot
from src.utils import write_json

LOGGER = logging.getLogger(__name__)


class VastApiClient:
    """Small Vast.ai API client with retries and response diagnostics."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout_seconds: int,
        debug_response_path: Path,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._debug_response_path = debug_response_path
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})
        retry = Retry(
            total=4,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retry))
        self._session.mount("http://", HTTPAdapter(max_retries=retry))

    def get_revenue_snapshot(self) -> RevenueSnapshot:
        """Fetch the current revenue snapshot from Vast.ai."""
        data = self._get_json("/users/current")
        now = datetime.now(timezone.utc)
        revenue = data.get("revenue") or data.get("earnings") or data
        try:
            return RevenueSnapshot(
                timestamp=now,
                hourly_usd=self._number(
                    revenue, ("hourly", "hourly_revenue", "earn_hour")
                ),
                daily_usd=self._number(
                    revenue, ("daily", "daily_revenue", "earn_day")
                ),
                weekly_usd=self._number(
                    revenue, ("weekly", "weekly_revenue", "earn_week")
                ),
                monthly_usd=self._number(
                    revenue, ("monthly", "monthly_revenue", "earn_month")
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            LOGGER.error(
                "Unable to parse Vast.ai revenue response. "
                "Enable DEBUG logging and inspect logs/api_response.json."
            )
            raise ValueError("Vast.ai revenue response structure is unsupported") from exc

    def _get_json(self, endpoint: str) -> dict[str, Any]:
        url = f"{self._base_url}{endpoint}"
        LOGGER.debug("Requesting Vast.ai endpoint %s", endpoint)
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        payload = response.json()
        if LOGGER.isEnabledFor(logging.DEBUG):
            write_json(self._debug_response_path, payload)
        if not isinstance(payload, dict):
            raise ValueError("Vast.ai response was not a JSON object")
        return payload

    @staticmethod
    def _number(data: Any, keys: tuple[str, ...]) -> float:
        if not isinstance(data, dict):
            raise TypeError("Revenue payload was not a JSON object")
        for key in keys:
            value = data.get(key)
            if isinstance(value, int | float | str):
                return float(value)
        raise KeyError(f"Missing revenue field; tried {', '.join(keys)}")
