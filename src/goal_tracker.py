"""Business-day daily goal calculations."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.models import GoalStatus
from src.utils import write_json


class GoalTracker:
    """Calculate progress for a 09:00 JST business day."""

    def __init__(self, path: Path, timezone: ZoneInfo, daily_goal_usd: float) -> None:
        self._path = path
        self._timezone = timezone
        self._daily_goal = daily_goal_usd

    def calculate(self, now: datetime, daily_revenue_usd: float) -> GoalStatus:
        """Calculate and persist current goal status."""
        local_now = now.astimezone(self._timezone)
        start = self._business_day_start(local_now)
        end = start + timedelta(days=1)
        elapsed_seconds = max((local_now - start).total_seconds(), 1.0)
        total_seconds = (end - start).total_seconds()
        current_percent = daily_revenue_usd / self._daily_goal * 100.0
        expected_percent = min(elapsed_seconds / total_seconds * 100.0, 100.0)
        estimate = daily_revenue_usd / elapsed_seconds * total_seconds
        status = GoalStatus(
            progress_usd=daily_revenue_usd,
            remaining_usd=max(self._daily_goal - daily_revenue_usd, 0.0),
            current_percent=current_percent,
            expected_percent=expected_percent,
            pace_delta_percent=current_percent - expected_percent,
            estimated_final_usd=estimate,
            on_track=current_percent >= expected_percent,
            business_day_start=start,
            business_day_end=end,
        )
        self._save(status)
        return status

    def _business_day_start(self, local_now: datetime) -> datetime:
        start = datetime.combine(local_now.date(), time(9), tzinfo=self._timezone)
        if local_now < start:
            return start - timedelta(days=1)
        return start

    def _save(self, status: GoalStatus) -> None:
        write_json(self._path, {
            "progress_usd": status.progress_usd,
            "remaining_usd": status.remaining_usd,
            "current_percent": status.current_percent,
            "expected_percent": status.expected_percent,
            "pace_delta_percent": status.pace_delta_percent,
            "estimated_final_usd": status.estimated_final_usd,
            "on_track": status.on_track,
            "business_day_start": status.business_day_start.isoformat(),
            "business_day_end": status.business_day_end.isoformat(),
        })
