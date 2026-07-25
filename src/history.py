"""Persistent revenue history."""
from __future__ import annotations

import csv
from pathlib import Path

from src.models import Change, Period, RevenueSnapshot
from src.utils import ensure_directory, read_json, utc_iso, write_json

CSV_HEADER = ["timestamp", "hourly", "daily", "weekly", "monthly"]


class HistoryStore:
    """Append-only JSON and CSV history store for reports."""

    def __init__(self, path: Path, csv_path: Path | None = None) -> None:
        self._path = path
        self._csv_path = csv_path or path.with_suffix(".csv")

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
        entry = self._entry(snapshot)
        history.append(entry)
        write_json(self._path, history[-5000:])
        self._append_csv(entry)
        return self._changes(snapshot, previous)

    def _append_csv(self, entry: dict[str, float | str]) -> None:
        ensure_directory(self._csv_path.parent)
        needs_header = not self._csv_path.exists() or self._csv_path.stat().st_size == 0
        with self._csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
            if needs_header:
                writer.writeheader()
            writer.writerow(entry)

    @staticmethod
    def _entry(snapshot: RevenueSnapshot) -> dict[str, float | str]:
        return {
            "timestamp": utc_iso(snapshot.timestamp),
            "hourly": snapshot.hourly_usd,
            "daily": snapshot.daily_usd,
            "weekly": snapshot.weekly_usd,
            "monthly": snapshot.monthly_usd,
        }

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
