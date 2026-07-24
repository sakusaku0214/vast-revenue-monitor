"""Domain models for Vast revenue monitoring."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Period(str, Enum):
    """Revenue aggregation periods."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True)
class Money:
    """A USD amount with a JPY conversion."""

    usd: float
    jpy: float


@dataclass(frozen=True)
class RevenueSnapshot:
    """Revenue values at a point in time."""

    timestamp: datetime
    hourly_usd: float
    daily_usd: float
    weekly_usd: float
    monthly_usd: float

    def value_for(self, period: Period) -> float:
        """Return the USD value for a period."""
        return {
            Period.HOURLY: self.hourly_usd,
            Period.DAILY: self.daily_usd,
            Period.WEEKLY: self.weekly_usd,
            Period.MONTHLY: self.monthly_usd,
        }[period]


@dataclass(frozen=True)
class Change:
    """Change from the previous report."""

    amount_usd: float
    percent: float


@dataclass(frozen=True)
class GoalStatus:
    """Daily business goal progress."""

    progress_usd: float
    remaining_usd: float
    percent: float
    estimated_final_usd: float
    on_track: bool
    business_day_start: datetime
    business_day_end: datetime
