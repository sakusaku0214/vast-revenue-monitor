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
        previous = float(events[-1]["balance"]) if events else sample.amount_usd
        boundary = self._weekly_boundary(local)
        confirmed_reset = self._confirm_weekly_reset(
            events, sample, boundary, previous
        )
        # A reset sample's remaining balance belongs to the new week.  Its exact
        # earning time is unknowable, so (as before) it is attributed to the
        # confirming observation rather than extrapolated across an interval.
        increment = (
            sample.amount_usd
            if confirmed_reset
            else max(sample.amount_usd - previous, 0.0)
        )
        event: dict[str, object] = {
            "timestamp": sample.timestamp.isoformat(),
            "balance": sample.amount_usd,
            "increment": increment,
        }
        if events:
            prior_time = datetime.fromisoformat(str(events[-1]["timestamp"]))
            if prior_time < boundary <= sample.timestamp and not confirmed_reset:
                event["pending_weekly_boundary"] = boundary.isoformat()
        if confirmed_reset:
            event["completed_weekly_balance"] = previous
            event["weekly_boundary"] = boundary.isoformat()
        events.append(event)
        events = events[-10000:]
        write_json(self._path, events)
        previous_timestamp = (
            datetime.fromisoformat(str(events[-2]["timestamp"])) if len(events) > 1 else None
        )
        yesterday_start = day_start - timedelta(days=1)
        completed_daily: tuple[float, ...] = ()
        completed_monthly: tuple[float, ...] = ()
        if previous_timestamp is not None:
            previous_local = previous_timestamp.astimezone(self._timezone)
            previous_day_start = self._period_start(
                previous_local, previous_local.date(), time(9)
            )
            if previous_day_start < day_start:
                completed_daily = (
                    self._sum_range(
                        events, day_start - timedelta(days=1), day_start
                    ),
                )
        current_month = self._payout_month(local)
        if confirmed_reset:
            closed_month = (boundary.year, boundary.month)
            if closed_month != current_month:
                completed_monthly = (self._monthly_total(events, *closed_month),)
        return RevenueSnapshot(
            timestamp=sample.timestamp,
            # "Hourly" is the newest successful observation, not a rolling
            # window or a normalized rate.  Using the event's increment avoids
            # double counting adjacent samples affected by clock drift.
            hourly_usd=increment,
            daily_usd=self._balance_since(events, day_start),
            weekly_usd=sample.amount_usd,
            monthly_usd=(
                self._monthly_total(events, *current_month) + sample.amount_usd
            ),
            yesterday_usd=self._sum_range(events, yesterday_start, day_start),
            completed_daily_usd=completed_daily,
            completed_weekly_usd=(previous,) if confirmed_reset else (),
            completed_monthly_usd=completed_monthly,
        )

    @staticmethod
    def _confirm_weekly_reset(
        events: list[dict[str, object]],
        sample: AccountBalance,
        boundary: datetime,
        previous_balance: float,
    ) -> bool:
        if not events:
            return False
        if sample.amount_usd >= previous_balance or sample.timestamp < boundary:
            return False
        boundary_key = boundary.isoformat()
        already_confirmed = any(
            event.get("weekly_boundary") == boundary_key for event in events
        )
        boundary_observed = (
            datetime.fromisoformat(str(events[-1]["timestamp"])) < boundary
            or any(event.get("pending_weekly_boundary") == boundary_key for event in events)
        )
        return boundary_observed and not already_confirmed

    def _weekly_boundary(self, local: datetime) -> datetime:
        day_start = self._period_start(local, local.date(), time(9))
        return day_start - timedelta(days=(day_start.weekday() - 5) % 7)

    def _payout_month(self, local: datetime) -> tuple[int, int]:
        """Return the month of the Saturday that will complete the running week."""
        week_end = self._weekly_boundary(local) + timedelta(days=7)
        return week_end.year, week_end.month

    def _period_start(self, now: datetime, period_date: date, boundary: time) -> datetime:
        start = datetime.combine(period_date, boundary, tzinfo=self._timezone)
        return start if now >= start else start - timedelta(days=1)

    @staticmethod
    def _balance_since(events: list[dict[str, object]], start: datetime) -> float:
        """Subtract the balance observed at a boundary from the current balance."""
        current = float(events[-1]["balance"])
        # A payout reset establishes a zero balance at the Saturday boundary,
        # even when the lower balance is first observed a little later.
        if any(
            "completed_weekly_balance" in event
            and datetime.fromisoformat(str(event.get("weekly_boundary", event["timestamp"])))
            >= start
            for event in events
        ):
            return current
        before = [
            event
            for event in events
            if datetime.fromisoformat(str(event["timestamp"])) < start
        ]
        baseline = float(before[-1]["balance"]) if before else float(events[0]["balance"])
        return max(current - baseline, 0.0)

    @staticmethod
    def _sum_since(events: list[dict[str, object]], start: datetime) -> float:
        return sum(
            float(event["increment"])
            for event in events
            if datetime.fromisoformat(str(event["timestamp"])) >= start
        )

    @staticmethod
    def _sum_range(
        events: list[dict[str, object]], start: datetime, end: datetime
    ) -> float:
        return sum(
            float(event["increment"])
            for event in events
            if start <= datetime.fromisoformat(str(event["timestamp"])) < end
        )

    def _monthly_total(
        self, events: list[dict[str, object]], year: int, month: int
    ) -> float:
        total = 0.0
        for event in events:
            if "completed_weekly_balance" not in event:
                continue
            boundary_value = event.get("weekly_boundary", event["timestamp"])
            closed = datetime.fromisoformat(str(boundary_value)).astimezone(self._timezone)
            if (closed.year, closed.month) == (year, month):
                total += float(event["completed_weekly_balance"])
        return total
