"""Persistent high-water revenue records."""
from __future__ import annotations

from pathlib import Path

from src.models import Period, RevenueSnapshot
from src.utils import read_json, utc_iso, write_json


class RecordsStore:
    """Track highest observed values for each revenue period."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def update(self, snapshot: RevenueSnapshot) -> set[Period]:
        """Persist new records and return periods that broke records."""
        records = read_json(self._path, lambda: {})
        broken: set[Period] = set()
        for period in Period:
            current = snapshot.value_for(period)
            best = float(records.get(period.value, {}).get("amount_usd", 0.0))
            if current > best:
                records[period.value] = {
                    "amount_usd": current,
                    "timestamp": utc_iso(snapshot.timestamp),
                }
                broken.add(period)
        write_json(self._path, records)
        return broken
