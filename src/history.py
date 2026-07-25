"""Persistent revenue history."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from src.models import Change, Period, RevenueSnapshot
from src.utils import ensure_directory, read_json, utc_iso, write_json

CSV_HEADER = ["timestamp", "hourly", "daily", "weekly", "monthly"]


class HistoryStore:
    """Append-only JSON history plus yearly rotated CSV exports."""

    def __init__(self, path: Path, csv_dir: Path | None = None) -> None:
        self._path = path
        self._csv_dir = csv_dir or path.parent

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
        self._append_csv(entry, snapshot.timestamp.year)
        return self._changes(snapshot, previous)

    def _append_csv(self, entry: dict[str, float | str], year: int) -> None:
        csv_path = self._csv_path(year)
        ensure_directory(csv_path.parent)
        needs_header = not csv_path.exists() or csv_path.stat().st_size == 0
        with csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
            if needs_header:
                writer.writeheader()
            writer.writerow(entry)
            handle.flush()
            os.fsync(handle.fileno())

    def _csv_path(self, year: int) -> Path:
        return self._csv_dir / f"history-{year}.csv"

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
