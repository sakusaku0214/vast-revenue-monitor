from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.models import AccountBalance
from src.revenue import RevenueAccumulator
from src.utils import read_json


def test_revenue_accumulator_uses_positive_balance_deltas(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    now = datetime(2026, 7, 25, 1, tzinfo=timezone.utc)

    baseline = accumulator.update(AccountBalance(now, 36.0))
    increased = accumulator.update(AccountBalance(now + timedelta(minutes=30), 38.5))
    payout = accumulator.update(AccountBalance(now + timedelta(minutes=45), 10.0))

    assert baseline.hourly_usd == 0.0
    assert increased.hourly_usd == 2.5
    assert payout.hourly_usd == 2.5

    recovered = accumulator.update(AccountBalance(now + timedelta(minutes=50), 11.0))
    assert recovered.hourly_usd == 3.5


def test_revenue_accumulator_resets_daily_total_at_0900(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    before = datetime(2026, 7, 26, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
    after = datetime(2026, 7, 26, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    accumulator.update(AccountBalance(before, 10.0))
    snapshot = accumulator.update(AccountBalance(after, 12.0))

    assert snapshot.daily_usd == 2.0


def test_weekly_reset_archives_previous_week_and_counts_post_reset_balance(tmp_path):
    path = tmp_path / "events.json"
    accumulator = RevenueAccumulator(path, ZoneInfo("Asia/Tokyo"))
    friday = datetime(2026, 7, 24, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    before_reset = datetime(2026, 7, 25, 8, 55, tzinfo=ZoneInfo("Asia/Tokyo"))
    after_reset = datetime(2026, 7, 25, 9, 2, tzinfo=ZoneInfo("Asia/Tokyo"))

    accumulator.update(AccountBalance(friday, 100.0))
    old_week = accumulator.update(AccountBalance(before_reset, 150.0))
    new_week = accumulator.update(AccountBalance(after_reset, 1.25))
    next_sample = accumulator.update(AccountBalance(after_reset + timedelta(hours=1), 2.0))
    events = read_json(path, list)

    assert old_week.weekly_usd == 150.0
    assert new_week.weekly_usd == 1.25
    assert next_sample.weekly_usd == 2.0
    assert events[-2]["completed_weekly_balance"] == 150.0
    assert events[-1]["balance"] == 2.0
