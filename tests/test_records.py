from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.models import Period, RevenueSnapshot
from src.records import RecordsStore


def test_records_store_returns_detailed_record_breaks(tmp_path):
    store = RecordsStore(tmp_path / "records.json")
    first = RevenueSnapshot(datetime(2026, 7, 24, tzinfo=timezone.utc), 1, 10, 20, 30)
    second = RevenueSnapshot(datetime(2026, 7, 25, tzinfo=timezone.utc), 1, 15, 18, 60)

    store.update(first)
    broken = store.update(second)

    assert set(broken) == {Period.DAILY, Period.MONTHLY}
    assert broken[Period.DAILY].previous_best_usd == 10
    assert broken[Period.DAILY].current_usd == 15
    assert broken[Period.DAILY].improvement_percent == 50


def test_weekly_record_survives_balance_reset(tmp_path):
    store = RecordsStore(tmp_path / "records.json")
    jst = ZoneInfo("Asia/Tokyo")
    before = RevenueSnapshot(datetime(2026, 7, 25, 8, 55, tzinfo=jst), 1, 10, 150, 200)
    after = RevenueSnapshot(datetime(2026, 7, 25, 9, 2, tzinfo=jst), 1, 1, 1.25, 201)

    store.update(before)
    store.update(after)

    assert store.highest()[Period.WEEKLY] == 150
