"""Service scheduler orchestration."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from src.config import AppConfig
from src.discord_embed import DiscordNotifier
from src.exchange_rate import ExchangeRateProvider
from src.goal_tracker import GoalTracker
from src.history import HistoryStore
from src.records import RecordsStore
from src.vast_api import VastApiClient
from src.weekly_reset import WeeklyResetLearner

LOGGER = logging.getLogger(__name__)


class RevenueMonitor:
    """Coordinate API clients, stores, business logic, and notifications."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._vast = VastApiClient(
            config.vast.api_key,
            config.vast.base_url,
            config.request_timeout_seconds,
        )
        self._exchange = ExchangeRateProvider(
            config.exchange.url,
            config.state_dir / "exchange_rate.json",
            config.exchange.timeout_seconds,
        )
        self._history = HistoryStore(config.state_dir / "history.json")
        self._records = RecordsStore(config.state_dir / "records.json")
        self._weekly_reset = WeeklyResetLearner(
            config.state_dir / "weekly_reset.json",
            config.timezone,
        )
        self._goal = GoalTracker(
            config.state_dir / "goal.json",
            config.timezone,
            config.daily_goal_usd,
        )
        self._discord = DiscordNotifier(
            config.discord_webhook_url,
            config.request_timeout_seconds,
        )

    def run_once(self) -> None:
        """Execute one report cycle."""
        snapshot = self._vast.get_revenue_snapshot()
        rate = self._exchange.get_usdjpy()
        previous_weekly = self._history.latest_weekly_usd()
        should_check_reset = (
            previous_weekly is not None
            and self._weekly_reset.should_monitor(snapshot.timestamp)
        )
        if should_check_reset:
            reset_detected = self._weekly_reset.observe(
                previous_weekly,
                snapshot.weekly_usd,
                snapshot.timestamp,
            )
            if reset_detected:
                LOGGER.info(
                    "Detected weekly revenue reset at %s",
                    snapshot.timestamp.isoformat(),
                )
        changes = self._history.append(snapshot)
        records = self._records.update(snapshot)
        goal = self._goal.calculate(snapshot.timestamp, snapshot.daily_usd)
        self._discord.send_report(snapshot, rate, changes, records, goal)
        LOGGER.info("Sent revenue report for %s", snapshot.timestamp.isoformat())

    def run_forever(self) -> None:
        """Run continuously, attempting a report near the top of every hour."""
        while True:
            try:
                self.run_once()
            except Exception:
                LOGGER.exception("Revenue report cycle failed")
            now = datetime.now(timezone.utc)
            sleep_seconds = 3600 - (now.minute * 60 + now.second)
            time.sleep(max(sleep_seconds, 60))
