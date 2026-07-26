"""Persistent high-water revenue records."""
from __future__ import annotations

from pathlib import Path

from src.models import Period, RecordBreak, RevenueSnapshot
from src.utils import read_json, utc_iso, write_json


class RecordsStore:
    """Track highest observed values for each revenue period."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def update(self, snapshot: RevenueSnapshot) -> dict[Period, RecordBreak]:
        """Persist new records and return detailed record-break information."""
        records = read_json(self._path, lambda: {})
        broken: dict[Period, RecordBreak] = {}
        for period in Period:
            current = snapshot.value_for(period)
            previous = float(records.get(period.value, {}).get("amount_usd", 0.0))
            if current > previous:
                improvement = ((current - previous) / previous * 100.0) if previous else 0.0
                records[period.value] = {
                    "amount_usd": current,
                    "timestamp": utc_iso(snapshot.timestamp),
                }
                broken[period] = RecordBreak(
                    period=period,
                    previous_best_usd=previous,
                    current_usd=current,
                    improvement_percent=improvement,
                )
        write_json(self._path, records)
        return broken

    def highest(self) -> dict[Period, float]:
        """Return all persisted high-water values, including zero defaults."""
        records = read_json(self._path, lambda: {})
        return {
            period: float(records.get(period.value, {}).get("amount_usd", 0.0))
            for period in Period
        }
