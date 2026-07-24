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
        start = datetime.combine(local_now.date(), time(9), tzinfo=self._timezone)
        if local_now < start:
            start -= timedelta(days=1)
        end = start + timedelta(days=1)
        elapsed = max((local_now - start).total_seconds(), 1.0)
        total = (end - start).total_seconds()
        estimate = daily_revenue_usd / elapsed * total
        remaining = max(self._daily_goal - daily_revenue_usd, 0.0)
        status = GoalStatus(
            progress_usd=daily_revenue_usd,
            remaining_usd=remaining,
            percent=daily_revenue_usd / self._daily_goal * 100.0,
            estimated_final_usd=estimate,
            on_track=estimate >= self._daily_goal,
            business_day_start=start,
            business_day_end=end,
        )
        write_json(self._path, {
            "progress_usd": status.progress_usd,
            "remaining_usd": status.remaining_usd,
            "percent": status.percent,
            "estimated_final_usd": status.estimated_final_usd,
            "on_track": status.on_track,
            "business_day_start": status.business_day_start.isoformat(),
            "business_day_end": status.business_day_end.isoformat(),
        })
        return status
