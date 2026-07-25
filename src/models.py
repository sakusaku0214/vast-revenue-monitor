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


class ReportStatus(str, Enum):
    """Overall report status used for Discord embed color selection."""

    NORMAL = "normal"
    ATTENTION = "attention"
    WARNING = "warning"
    RECORD = "record"


@dataclass(frozen=True)
class GpuAvailability:
    """Current GPU rental availability summary."""

    total: int
    rented: int

    @property
    def all_available(self) -> bool:
        """Return true when no GPUs appear to be rented."""
        return self.total > 0 and self.rented == 0


@dataclass(frozen=True)
class RevenueSnapshot:
    """Revenue values at a point in time."""

    timestamp: datetime
    hourly_usd: float
    daily_usd: float
    weekly_usd: float
    monthly_usd: float
    gpu_availability: GpuAvailability | None = None

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
class RecordBreak:
    """Details for a newly broken revenue record."""

    period: Period
    previous_best_usd: float
    current_usd: float
    improvement_percent: float


@dataclass(frozen=True)
class GoalStatus:
    """Daily business goal progress."""

    progress_usd: float
    remaining_usd: float
    current_percent: float
    expected_percent: float
    pace_delta_percent: float
    estimated_final_usd: float
    on_track: bool
    business_day_start: datetime
    business_day_end: datetime
