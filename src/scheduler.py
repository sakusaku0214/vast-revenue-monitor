"""Service scheduler orchestration."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

from src.config import AppConfig
from src.discord_embed import DiscordNotifier
from src.exchange_rate import ExchangeRateProvider
from src.goal_tracker import GoalTracker
from src.history import HistoryStore
from src.models import RevenueSnapshot
from src.records import RecordsStore
from src.revenue import RevenueAccumulator
from src.vast_api import VastApiClient, VastApiSchemaError
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
            config.log_dir / "api_response.json",
            revenue_endpoint=config.vast.revenue_endpoint,
            auth_mode=config.vast.auth_mode,
            balance_field=config.vast.balance_field,
        )
        self._exchange = ExchangeRateProvider(
            config.exchange.urls,
            config.state_dir / "exchange_rate.json",
            config.exchange.timeout_seconds,
        )
        self._history = HistoryStore(config.state_dir / "history.json")
        self._records = RecordsStore(config.state_dir / "records.json")
        self._revenue = RevenueAccumulator(
            config.state_dir / "revenue_events.json", config.timezone
        )
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
            config.weekly_goal_usd,
            config.detailed_report,
            config.timezone.key,
            config.language,
        )

    def run_once(self) -> None:
        """Execute one report cycle."""
        snapshot = self._fetch_snapshot_with_alert()
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
        highest = self._records.highest()
        goal = self._goal.calculate(snapshot.timestamp, snapshot.daily_usd)
        self._discord.send_report(snapshot, rate, changes, records, goal, highest)
        LOGGER.info("Sent revenue report for %s", snapshot.timestamp.isoformat())

    def validate_connections(self) -> None:
        """Validate required upstream APIs without posting or changing report state."""
        sample = self._vast.get_account_balance()
        rate = self._exchange.get_usdjpy()
        self._discord.validate_webhook()
        LOGGER.info(
            "Connectivity validation succeeded at %s with USDJPY %.4f",
            sample.timestamp.isoformat(),
            rate,
        )

    def _fetch_snapshot_with_alert(self) -> RevenueSnapshot:
        """Fetch a snapshot and make a best-effort schema-change notification."""
        try:
            return self._revenue.update(self._vast.get_account_balance())
        except VastApiSchemaError as exc:
            LOGGER.exception("Vast.ai API schema parsing failed")
            try:
                self._discord.send_schema_alert(str(exc))
            except Exception:  # noqa: BLE001 - preserve the primary API failure
                LOGGER.exception("Unable to send Vast.ai schema alert to Discord")
            raise

    def run_forever(self) -> None:
        """Report once at startup and near the top of each subsequent hour."""
        self._run_safely(self.run_once, "Initial revenue report failed")
        while True:
            now = datetime.now(timezone.utc)
            sleep_seconds = 3600 - (now.minute * 60 + now.second)
            time.sleep(max(sleep_seconds, 60))
            self._run_safely(self.run_once, "Revenue report cycle failed")

    @staticmethod
    def _run_safely(action: Callable[[], None], failure_message: str) -> None:
        """Run a scheduled callable without terminating the service loop."""
        try:
            action()
        except Exception:  # noqa: BLE001 - long-running scheduler boundary
            LOGGER.exception(failure_message)
