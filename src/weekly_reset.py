"""Adaptive weekly reset detection."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.utils import read_json, write_json

WIDE_MINUTES = [-20, -15, -10, -5, 0, 2, 5, 10, 15, 20]
MIN_PREVIOUS_WEEKLY_USD = 50.0
MAX_RESET_WEEKLY_USD = 3.0
MIN_DROP_RATIO = 0.9
FULL_SCAN_INTERVAL_WEEKS = 4


class WeeklyResetLearner:
    """Learn and monitor Vast.ai weekly reset time around Saturday 09:00 JST."""

    def __init__(self, path: Path, timezone: ZoneInfo) -> None:
        self._path = path
        self._timezone = timezone

    def should_monitor(self, now: datetime) -> bool:
        """Return true when the scheduler should sample for reset detection."""
        local = now.astimezone(self._timezone)
        if local.weekday() != 5:
            return False
        state = read_json(self._path, self._default_state)
        if self._needs_full_scan(local, state):
            return self._within_wide_window(local)
        learned = state.get("learned_time")
        if not learned:
            return self._within_wide_window(local)
        learned_time = time.fromisoformat(str(learned))
        target = datetime.combine(local.date(), learned_time, tzinfo=self._timezone)
        return abs((local - target).total_seconds()) <= 180

    def observe(
        self,
        previous_weekly: float,
        current_weekly: float,
        now: datetime,
    ) -> bool:
        """Learn a reset only when all reset-confidence rules are satisfied."""
        if not self._is_reset(previous_weekly, current_weekly):
            return False
        local = now.astimezone(self._timezone)
        state = read_json(self._path, self._default_state)
        reset_time = local.time().replace(second=0, microsecond=0)
        state["learned_time"] = reset_time.isoformat()
        state["last_reset_timestamp"] = local.isoformat()
        state["observations"] = int(state.get("observations", 0)) + 1
        if self._within_wide_window(local):
            state["last_full_scan"] = local.date().isoformat()
        write_json(self._path, state)
        return True

    def _needs_full_scan(self, local: datetime, state: dict[str, object]) -> bool:
        if not state.get("learned_time"):
            return True
        last_full_scan = state.get("last_full_scan")
        if not last_full_scan:
            return True
        last_scan = datetime.fromisoformat(str(last_full_scan)).date()
        return (local.date() - last_scan).days >= FULL_SCAN_INTERVAL_WEEKS * 7

    def _within_wide_window(self, local: datetime) -> bool:
        base = datetime.combine(local.date(), time(9), tzinfo=self._timezone)
        return any(
            abs((local - (base + timedelta(minutes=minute))).total_seconds()) < 60
            for minute in WIDE_MINUTES
        )

    @staticmethod
    def _is_reset(previous_weekly: float, current_weekly: float) -> bool:
        if previous_weekly <= MIN_PREVIOUS_WEEKLY_USD:
            return False
        if current_weekly >= MAX_RESET_WEEKLY_USD:
            return False
        drop_ratio = (previous_weekly - current_weekly) / previous_weekly
        return drop_ratio >= MIN_DROP_RATIO

    @staticmethod
    def _default_state() -> dict[str, object]:
        return {
            "learned_time": None,
            "last_reset_timestamp": None,
            "last_full_scan": None,
            "observations": 0,
        }
