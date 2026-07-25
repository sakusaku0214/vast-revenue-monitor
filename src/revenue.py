"""Derive period revenue from successive Vast.ai account-balance samples."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.models import AccountBalance, RevenueSnapshot
from src.utils import read_json, write_json


class RevenueAccumulator:
    """Persist positive balance deltas and aggregate them into report periods."""

    def __init__(self, path: Path, timezone: ZoneInfo) -> None:
        self._path = path
        self._timezone = timezone

    def update(self, sample: AccountBalance) -> RevenueSnapshot:
        """Store a sample and return revenue derived from observed balance growth."""
        events = read_json(self._path, lambda: [])
        if not isinstance(events, list):
            raise ValueError("Revenue events state must be a JSON array")
        local = sample.timestamp.astimezone(self._timezone)
        day_start = self._period_start(local, local.date(), time(9))
        week_start = day_start - timedelta(days=(day_start.weekday() - 5) % 7)
        previous = float(events[-1]["balance"]) if events else sample.amount_usd
        crossed_reset = self._crossed_weekly_reset(events, sample, week_start)
        increment = (
            sample.amount_usd
            if crossed_reset
            else max(sample.amount_usd - previous, 0.0)
        )
        event: dict[str, object] = {
            "timestamp": sample.timestamp.isoformat(),
            "balance": sample.amount_usd,
            "increment": increment,
        }
        if crossed_reset:
            event["completed_weekly_balance"] = previous
        events.append(event)
        events = events[-10000:]
        write_json(self._path, events)
        month_start = datetime.combine(
            local.date().replace(day=1), time(9), tzinfo=self._timezone
        )
        if local < month_start:
            previous_month = local.date().replace(day=1) - timedelta(days=1)
            month_start = datetime.combine(
                previous_month.replace(day=1), time(9), tzinfo=self._timezone
            )
        return RevenueSnapshot(
            timestamp=sample.timestamp,
            hourly_usd=self._sum_since(events, sample.timestamp - timedelta(hours=1)),
            daily_usd=self._sum_since(events, day_start),
            weekly_usd=sample.amount_usd,
            monthly_usd=self._sum_since(events, month_start),
        )

    @staticmethod
    def _crossed_weekly_reset(
        events: list[dict[str, object]],
        sample: AccountBalance,
        week_start: datetime,
    ) -> bool:
        if not events:
            return False
        previous_timestamp = datetime.fromisoformat(str(events[-1]["timestamp"]))
        return previous_timestamp < week_start <= sample.timestamp

    def _period_start(self, now: datetime, period_date: date, boundary: time) -> datetime:
        start = datetime.combine(period_date, boundary, tzinfo=self._timezone)
        return start if now >= start else start - timedelta(days=1)

    @staticmethod
    def _sum_since(events: list[dict[str, object]], start: datetime) -> float:
        return sum(
            float(event["increment"])
            for event in events
            if datetime.fromisoformat(str(event["timestamp"])) >= start
        )
