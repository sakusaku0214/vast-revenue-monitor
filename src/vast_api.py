"""Vast.ai API client."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import GpuAvailability, RevenueSnapshot
from src.utils import write_json

LOGGER = logging.getLogger(__name__)


class VastApiSchemaError(ValueError):
    """Raised when the Vast.ai revenue response cannot be parsed safely."""


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
                gpu_availability=self._gpu_availability(data),
            )
        except (KeyError, TypeError, ValueError) as exc:
            LOGGER.error(
                "Unable to parse Vast.ai revenue response. "
                "Enable DEBUG logging and inspect logs/api_response.json."
            )
            raise VastApiSchemaError(
                "Vast.ai revenue response structure is unsupported"
            ) from exc

    def _get_json(self, endpoint: str) -> dict[str, Any]:
        url = f"{self._base_url}{endpoint}"
        LOGGER.debug("Requesting Vast.ai endpoint %s", endpoint)
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        payload = response.json()
        if LOGGER.isEnabledFor(logging.DEBUG):
            try:
                write_json(self._debug_response_path, payload)
            except (OSError, TypeError, ValueError):
                LOGGER.exception("Unable to persist Vast.ai debug response")
        if not isinstance(payload, dict):
            raise VastApiSchemaError("Vast.ai response was not a JSON object")
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

    @staticmethod
    def _gpu_availability(data: dict[str, Any]) -> GpuAvailability | None:
        for key in ("machines", "instances", "offers"):
            value = data.get(key)
            if isinstance(value, list) and value:
                return VastApiClient._availability_from_items(value)
        total = VastApiClient._optional_int(data, ("total_gpus", "gpu_total"))
        rented = VastApiClient._optional_int(data, ("rented_gpus", "gpu_rented"))
        if total is not None and rented is not None:
            return GpuAvailability(total=total, rented=rented)
        return None

    @staticmethod
    def _availability_from_items(items: list[Any]) -> GpuAvailability:
        total = 0
        rented = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            count = VastApiClient._item_gpu_count(item)
            total += count
            if VastApiClient._item_is_rented(item):
                rented += count
        return GpuAvailability(total=total, rented=rented)

    @staticmethod
    def _item_gpu_count(item: dict[str, Any]) -> int:
        for key in ("num_gpus", "gpu_count", "gpus"):
            value = item.get(key)
            if isinstance(value, int | float | str):
                return max(int(value), 0)
        return 1

    @staticmethod
    def _item_is_rented(item: dict[str, Any]) -> bool:
        for key in ("rented", "in_use", "is_rented"):
            value = item.get(key)
            if isinstance(value, bool):
                return value
        status = item.get("status") or item.get("machine_status")
        return str(status).lower() in {"running", "rented", "occupied"}

    @staticmethod
    def _optional_int(data: dict[str, Any], keys: tuple[str, ...]) -> int | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, int | float | str):
                return int(value)
        return None
