"""Persistent revenue history."""
from __future__ import annotations

from pathlib import Path

from src.models import Change, Period, RevenueSnapshot
from src.utils import read_json, utc_iso, write_json


class HistoryStore:
    """Append-only JSON history store for reports."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def latest_weekly_usd(self) -> float | None:
        """Return the latest stored weekly revenue value."""
        history = read_json(self._path, lambda: [])
        if not history:
            return None
        return float(history[-1].get("weekly", 0.0))

    def append(self, snapshot: RevenueSnapshot) -> dict[str, Change]:
        """Append a snapshot and return changes versus the previous snapshot."""
        history = read_json(self._path, lambda: [])
        previous = history[-1] if history else None
        entry = {
            "timestamp": utc_iso(snapshot.timestamp),
            "hourly": snapshot.hourly_usd,
            "daily": snapshot.daily_usd,
            "weekly": snapshot.weekly_usd,
            "monthly": snapshot.monthly_usd,
        }
        history.append(entry)
        write_json(self._path, history[-5000:])
        return self._changes(snapshot, previous)

    @staticmethod
    def _changes(
        snapshot: RevenueSnapshot,
        previous: dict[str, float] | None,
    ) -> dict[str, Change]:
        changes: dict[str, Change] = {}
        for period in Period:
            current = snapshot.value_for(period)
            old = float(previous.get(period.value, 0.0)) if previous else 0.0
            amount = current - old
            percent = (amount / old * 100.0) if old else 0.0
            changes[period.value] = Change(amount_usd=amount, percent=percent)
        return changes
