"""Configuration loading and validation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class VastConfig:
    """Vast.ai API configuration."""

    api_key: str
    base_url: str = "https://console.vast.ai/api/v0"


@dataclass(frozen=True)
class ExchangeConfig:
    """Exchange-rate provider configuration."""

    url: str = "https://open.er-api.com/v6/latest/USD"
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
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        required = ["discord_webhook_url", "vast_api_key"]
        missing = [key for key in required if not raw.get(key)]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required configuration keys: {joined}")
        return cls(
            discord_webhook_url=str(raw["discord_webhook_url"]),
            vast=VastConfig(
                api_key=str(raw["vast_api_key"]),
                base_url=str(
                    raw.get("vast_base_url", "https://console.vast.ai/api/v0")
                ),
            ),
            daily_goal_usd=float(raw.get("daily_goal_usd", 120.0)),
            timezone=ZoneInfo(str(raw.get("timezone", "Asia/Tokyo"))),
            exchange=ExchangeConfig(
                url=str(
                    raw.get(
                        "exchange_api_url",
                        "https://open.er-api.com/v6/latest/USD",
                    )
                ),
                timeout_seconds=int(raw.get("exchange_timeout_seconds", 15)),
            ),
            log_level=str(raw.get("log_level", "INFO")),
            state_dir=Path(str(raw.get("state_dir", "state"))),
            log_dir=Path(str(raw.get("log_dir", "logs"))),
            request_timeout_seconds=int(raw.get("request_timeout_seconds", 30)),
        )
