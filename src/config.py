"""Configuration loading and validation."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

DEFAULT_EXCHANGE_API_URLS = (
    "https://open.er-api.com/v6/latest/USD",
    "https://api.frankfurter.app/latest?from=USD&to=JPY",
    "https://api.exchangerate.host/latest?base=USD&symbols=JPY",
)


@dataclass(frozen=True)
class VastConfig:
    """Vast.ai API configuration."""

    api_key: str
    base_url: str = "https://console.vast.ai/api/v0"
    revenue_endpoint: str = "/machines/"
    auth_mode: str = "query"


@dataclass(frozen=True)
class ExchangeConfig:
    """Exchange-rate provider configuration."""

    urls: tuple[str, ...]
    timeout_seconds: int = 15


@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""

    discord_webhook_url: str
    vast: VastConfig
    daily_goal_usd: float
    timezone: ZoneInfo
    exchange: ExchangeConfig
    log_level: str
    state_dir: Path
    log_dir: Path
    request_timeout_seconds: int

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        """Load configuration from a JSON file."""
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError as exc:
            raise ValueError(f"Configuration file does not exist: {path}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to read configuration file {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError("Configuration root must be a JSON object")
        required = ["discord_webhook_url", "vast_api_key"]
        missing = [key for key in required if not raw.get(key)]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required configuration keys: {joined}")
        config = cls(
            discord_webhook_url=str(raw["discord_webhook_url"]),
            vast=VastConfig(
                api_key=str(raw["vast_api_key"]),
                base_url=str(
                    raw.get("vast_base_url", "https://console.vast.ai/api/v0")
                ),
                revenue_endpoint=str(raw.get("vast_revenue_endpoint", "/machines/")),
                auth_mode=str(raw.get("vast_auth_mode", "query")),
            ),
            daily_goal_usd=float(raw.get("daily_goal_usd", 120.0)),
            timezone=ZoneInfo(str(raw.get("timezone", "Asia/Tokyo"))),
            exchange=ExchangeConfig(
                urls=cls._exchange_urls(raw),
                timeout_seconds=int(raw.get("exchange_timeout_seconds", 15)),
            ),
            log_level=str(raw.get("log_level", "INFO")),
            state_dir=Path(str(raw.get("state_dir", "state"))),
            log_dir=Path(str(raw.get("log_dir", "logs"))),
            request_timeout_seconds=int(raw.get("request_timeout_seconds", 30)),
        )
        cls._validate(config)
        return config

    @staticmethod
    def _validate(config: "AppConfig") -> None:
        """Reject unsafe or nonsensical settings before the service starts."""
        if "REPLACE_ME" in config.discord_webhook_url or "REPLACE_ME" in config.vast.api_key:
            raise ValueError("Replace the example Discord webhook and Vast.ai API key")
        AppConfig._require_https(config.discord_webhook_url, "discord_webhook_url")
        webhook = urlparse(config.discord_webhook_url)
        if webhook.hostname not in {"discord.com", "discordapp.com"}:
            raise ValueError("discord_webhook_url must use an official Discord host")
        if not webhook.path.startswith("/api/webhooks/"):
            raise ValueError("discord_webhook_url must be a Discord webhook endpoint")
        AppConfig._require_https(config.vast.base_url, "vast_base_url")
        if not config.vast.revenue_endpoint.startswith("/"):
            raise ValueError("vast_revenue_endpoint must start with /")
        if config.vast.auth_mode not in {"query", "bearer"}:
            raise ValueError("vast_auth_mode must be query or bearer")
        for url in config.exchange.urls:
            AppConfig._require_https(url, "exchange_api_urls")
        if not math.isfinite(config.daily_goal_usd) or config.daily_goal_usd <= 0:
            raise ValueError("daily_goal_usd must be a positive finite number")
        if not 1 <= config.request_timeout_seconds <= 300:
            raise ValueError("request_timeout_seconds must be between 1 and 300")
        if not 1 <= config.exchange.timeout_seconds <= 300:
            raise ValueError("exchange_timeout_seconds must be between 1 and 300")
        if config.log_level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")

    @staticmethod
    def _require_https(value: str, setting: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"{setting} must contain a valid HTTPS URL")

    @staticmethod
    def _exchange_urls(raw: dict[str, object]) -> tuple[str, ...]:
        configured = raw.get("exchange_api_urls")
        if isinstance(configured, list) and configured:
            return tuple(str(url) for url in configured)
        legacy_url = raw.get("exchange_api_url")
        if legacy_url:
            return (str(legacy_url), *DEFAULT_EXCHANGE_API_URLS[1:])
        return DEFAULT_EXCHANGE_API_URLS
