from __future__ import annotations

import csv
from datetime import datetime, timezone

from src.history import HistoryStore
from src.models import RevenueSnapshot


def test_history_appends_json_and_csv(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    snapshot = RevenueSnapshot(
        timestamp=datetime(2026, 7, 24, 0, tzinfo=timezone.utc),
        hourly_usd=1.0,
        daily_usd=2.0,
        weekly_usd=3.0,
        monthly_usd=4.0,
    )

    changes = store.append(snapshot)

    assert changes["daily"].amount_usd == 2.0
    with (tmp_path / "history.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["timestamp"] == "2026-07-24T00:00:00+00:00"
    assert rows[0]["hourly"] == "1.0"


def test_history_change_calculation_uses_previous_snapshot(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    first = RevenueSnapshot(datetime(2026, 7, 24, 0, tzinfo=timezone.utc), 1, 10, 20, 30)
    second = RevenueSnapshot(datetime(2026, 7, 24, 1, tzinfo=timezone.utc), 2, 15, 10, 60)

    store.append(first)
    changes = store.append(second)

    assert changes["daily"].amount_usd == 5
    assert changes["daily"].percent == 50
    assert changes["weekly"].amount_usd == -10
