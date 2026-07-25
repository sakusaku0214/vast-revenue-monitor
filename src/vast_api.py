"""Vast.ai API client."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import AccountBalance, GpuAvailability
from src.utils import write_json

LOGGER = logging.getLogger(__name__)
SENSITIVE_FIELDS = {
    "api_key",
    "crisp_hmac",
    "discord_id",
    "email",
    "escalation_email",
    "escalation_phone_number",
    "paypal_email",
    "phone_number",
    "ssh_key",
    "wise_email",
}


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
        revenue_endpoint: str = "/users/current/",
        auth_mode: str = "query",
        balance_field: str = "balance",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._revenue_endpoint = revenue_endpoint
        self._api_key = api_key
        self._auth_mode = auth_mode
        self._balance_field = balance_field
        self._timeout = timeout_seconds
        self._debug_response_path = debug_response_path
        self._session = requests.Session()
        if auth_mode == "bearer":
            self._session.headers.update({"Authorization": f"Bearer {api_key}"})
        retry = Retry(
            total=4,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retry))
        self._session.mount("http://", HTTPAdapter(max_retries=retry))

    def get_account_balance(self) -> AccountBalance:
        """Fetch the account balance used as the local revenue counter."""
        data = self._get_json(self._revenue_endpoint)
        try:
            amount = self._strict_number(data, self._balance_field)
            if amount < 0:
                raise ValueError("Vast.ai account balance must not be negative")
            return AccountBalance(datetime.now(timezone.utc), amount)
        except (KeyError, TypeError, ValueError) as exc:
            self._persist_diagnostic(data)
            keys = self._keys_for_diagnostic(data)
            raise VastApiSchemaError(
                f"Vast.ai response lacks numeric {self._balance_field!r}; keys: {keys}"
            ) from exc

    @staticmethod
    def _strict_number(data: Any, key: str) -> float:
        """Read an API numeric field without coercing nulls, strings, or booleans."""
        if not isinstance(data, dict):
            raise TypeError("Vast.ai response was not a JSON object")
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"Vast.ai field {key!r} was not numeric")
        return float(value)

    def _get_json(self, endpoint: str) -> dict[str, Any]:
        url = f"{self._base_url}{endpoint}"
        LOGGER.debug("Requesting Vast.ai endpoint %s", endpoint)
        params = {"api_key": self._api_key} if self._auth_mode == "query" else None
        response = self._session.get(url, params=params, timeout=self._timeout)
        try:
            response.raise_for_status()
            payload = response.json()
        finally:
            response.close()
        if LOGGER.isEnabledFor(logging.DEBUG):
            self._persist_diagnostic(payload)
        if not isinstance(payload, dict):
            raise VastApiSchemaError("Vast.ai response was not a JSON object")
        return payload

    def _persist_diagnostic(self, payload: Any) -> None:
        """Persist the latest payload without hiding the original API failure."""
        try:
            write_json(self._debug_response_path, self._redact(payload))
        except (OSError, TypeError, ValueError):
            LOGGER.exception("Unable to persist Vast.ai API diagnostic response")

    @staticmethod
    def _keys_for_diagnostic(payload: Any) -> list[str]:
        """Return only field names so normal logs do not expose API values."""
        if not isinstance(payload, dict):
            return []
        return sorted(str(key) for key in payload)

    @classmethod
    def _redact(cls, payload: Any) -> Any:
        """Remove account secrets and personal information from diagnostics."""
        if isinstance(payload, dict):
            return {
                str(key): "[REDACTED]" if str(key).lower() in SENSITIVE_FIELDS
                else cls._redact(value)
                for key, value in payload.items()
            }
        if isinstance(payload, list):
            return [cls._redact(item) for item in payload]
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
