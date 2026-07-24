"""Adaptive weekly reset detection."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.utils import read_json, write_json

WIDE_MINUTES = [-20, -15, -10, -5, 0, 2, 5, 10, 15, 20]


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
        weeks = int(state.get("observations", 0))
        learned = state.get("learned_time")
        if weeks < 4 or weeks % 4 == 0 or not learned:
            base = datetime.combine(local.date(), time(9), tzinfo=self._timezone)
            return any(
                abs((local - (base + timedelta(minutes=m))).total_seconds()) < 60
                for m in WIDE_MINUTES
            )
        learned_time = time.fromisoformat(str(learned))
        target = datetime.combine(local.date(), learned_time, tzinfo=self._timezone)
        return abs((local - target).total_seconds()) <= 180

    def observe(
        self,
        previous_weekly: float,
        current_weekly: float,
        now: datetime,
    ) -> bool:
        """Record a reset when weekly revenue drops sharply."""
        if current_weekly >= previous_weekly or previous_weekly <= 0:
            return False
        local = now.astimezone(self._timezone)
        state = read_json(self._path, self._default_state)
        reset_time = local.time().replace(second=0, microsecond=0)
        state["learned_time"] = reset_time.isoformat()
        state["last_reset_timestamp"] = local.isoformat()
        state["observations"] = int(state.get("observations", 0)) + 1
        write_json(self._path, state)
        return True

    @staticmethod
    def _default_state() -> dict[str, object]:
        return {"learned_time": None, "last_reset_timestamp": None, "observations": 0}
