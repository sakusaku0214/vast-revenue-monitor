from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

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
    assert payout.hourly_usd == 0.0

    recovered = accumulator.update(AccountBalance(now + timedelta(minutes=50), 11.0))
    assert recovered.hourly_usd == 1.0


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


def test_hourly_is_latest_increment_after_restart_and_irregular_delay(tmp_path):
    path = tmp_path / "events.json"
    timezone_jst = ZoneInfo("Asia/Tokyo")
    start = datetime(2026, 7, 26, 10, 0, tzinfo=timezone_jst)
    RevenueAccumulator(path, timezone_jst).update(AccountBalance(start, 10.0))
    RevenueAccumulator(path, timezone_jst).update(
        AccountBalance(start + timedelta(minutes=58), 13.0)
    )
    snapshot = RevenueAccumulator(path, timezone_jst).update(
        AccountBalance(start + timedelta(minutes=62), 15.0)
    )

    assert snapshot.hourly_usd == 2.0


def test_daily_assigns_boundary_crossing_delta_to_observation_day(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    before = datetime(2026, 7, 26, 8, 59, tzinfo=ZoneInfo("Asia/Tokyo"))
    after = datetime(2026, 7, 26, 9, 1, tzinfo=ZoneInfo("Asia/Tokyo"))

    accumulator.update(AccountBalance(before, 20.0))
    snapshot = accumulator.update(AccountBalance(after, 23.0))

    assert snapshot.daily_usd == 3.0


def test_observations_59m59s_apart_do_not_double_count_hourly(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("UTC"))
    start = datetime(2026, 7, 26, 1, 0, 1, tzinfo=timezone.utc)
    accumulator.update(AccountBalance(start - timedelta(hours=1), 100.0))
    first = accumulator.update(AccountBalance(start, 103.56739328))
    second = accumulator.update(
        AccountBalance(start + timedelta(minutes=59, seconds=59), 108.92604038)
    )

    assert first.hourly_usd == pytest.approx(3.56739328)
    assert second.hourly_usd == pytest.approx(5.35864710)
