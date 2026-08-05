from __future__ import annotations

from datetime import datetime, timezone

from src.models import Period, RevenueSnapshot
from src.records import RecordsStore


def test_records_store_returns_detailed_record_breaks(tmp_path):
    store = RecordsStore(tmp_path / "records.json")
    first = RevenueSnapshot(
        datetime(2026, 7, 24, tzinfo=timezone.utc), 1, 10, 20, 30,
        completed_daily_usd=(10,), completed_monthly_usd=(30,),
    )
    second = RevenueSnapshot(
        datetime(2026, 7, 25, tzinfo=timezone.utc), 1, 15, 18, 60,
        completed_daily_usd=(15,), completed_monthly_usd=(60,),
    )

    store.update(first)
    broken = store.update(second)

    assert set(broken) == {Period.DAILY, Period.MONTHLY}
    assert broken[Period.DAILY].previous_best_usd == 10
    assert broken[Period.DAILY].current_usd == 15
    assert broken[Period.DAILY].improvement_percent == 50


def test_monthly_ath_uses_completed_months_not_running_months(tmp_path):
    store = RecordsStore(tmp_path / "records.json")
    running = RevenueSnapshot(datetime(2026, 8, 1, tzinfo=timezone.utc), 1, 2, 1200, 1200)
    completed = RevenueSnapshot(
        datetime(2026, 8, 8, tzinfo=timezone.utc), 1, 2, 3, 4,
        completed_monthly_usd=(914.96,),
    )

    assert Period.MONTHLY not in store.update(running)
    broken = store.update(completed)

    assert broken[Period.MONTHLY].current_usd == 914.96
