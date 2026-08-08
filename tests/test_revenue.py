from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.models import AccountBalance, Period
from src.records import RecordsStore
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


def test_delayed_observation_crossing_0900_stays_with_interval_start_day(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    before = datetime(2026, 7, 26, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
    after = datetime(2026, 7, 26, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    accumulator.update(AccountBalance(before, 10.0))
    snapshot = accumulator.update(AccountBalance(after, 12.0))

    assert snapshot.hourly_usd == 2.0
    assert snapshot.daily_usd == 0.0
    assert snapshot.yesterday_usd == 2.0


def test_exact_production_style_daily_rollover_sequence(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    boundary = datetime(2026, 8, 7, 9, 0, tzinfo=jst)

    accumulator.update(AccountBalance(boundary - timedelta(days=1), 100.0))
    at_0800 = accumulator.update(
        AccountBalance(boundary - timedelta(hours=1), 227.04)
    )
    at_0900 = accumulator.update(AccountBalance(boundary, 232.34))
    at_1000 = accumulator.update(
        AccountBalance(boundary + timedelta(hours=1), 237.54)
    )

    assert at_0800.daily_usd == pytest.approx(127.04)
    assert at_0900.hourly_usd == pytest.approx(5.30)
    assert at_0900.daily_usd == pytest.approx(0.0)
    assert at_0900.yesterday_usd == pytest.approx(132.34)
    assert at_0900.completed_daily_usd == pytest.approx((132.34,))
    assert at_1000.hourly_usd == pytest.approx(5.20)
    assert at_1000.daily_usd == pytest.approx(5.20)
    assert at_1000.yesterday_usd == pytest.approx(132.34)


def test_intervals_on_each_side_of_exact_0900_have_one_daily_owner(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    boundary = datetime(2026, 8, 7, 9, tzinfo=jst)

    accumulator.update(AccountBalance(boundary - timedelta(seconds=1), 10.0))
    at_boundary = accumulator.update(AccountBalance(boundary, 12.0))
    after_boundary = accumulator.update(AccountBalance(boundary + timedelta(hours=1), 15.0))

    assert at_boundary.daily_usd == 0.0
    assert at_boundary.yesterday_usd == 2.0
    assert after_boundary.daily_usd == 3.0
    assert after_boundary.yesterday_usd == 2.0


def test_microsecond_interval_ending_at_0900_belongs_to_previous_day(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    boundary = datetime(2026, 8, 7, 9, tzinfo=jst)

    accumulator.update(AccountBalance(boundary - timedelta(microseconds=1), 10.0))
    at_boundary = accumulator.update(AccountBalance(boundary, 11.25))
    after = accumulator.update(AccountBalance(boundary + timedelta(microseconds=1), 12.0))

    assert at_boundary.daily_usd == 0.0
    assert at_boundary.yesterday_usd == pytest.approx(1.25)
    assert after.daily_usd == pytest.approx(0.75)
    assert after.yesterday_usd == pytest.approx(1.25)


def test_missing_boundary_sample_does_not_split_or_extrapolate_increment(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    boundary = datetime(2026, 8, 7, 9, tzinfo=jst)

    accumulator.update(AccountBalance(boundary - timedelta(hours=2), 20.0))
    delayed = accumulator.update(AccountBalance(boundary + timedelta(hours=2), 24.5))

    assert delayed.hourly_usd == pytest.approx(4.5)
    assert delayed.daily_usd == 0.0
    assert delayed.yesterday_usd == pytest.approx(4.5)


def test_restart_on_both_sides_of_0900_preserves_daily_attribution(tmp_path):
    path = tmp_path / "events.json"
    jst = ZoneInfo("Asia/Tokyo")
    boundary = datetime(2026, 8, 7, 9, tzinfo=jst)
    before_restart = RevenueAccumulator(path, jst)
    before_restart.update(AccountBalance(boundary - timedelta(hours=1), 100.0))

    at_boundary = RevenueAccumulator(path, jst).update(AccountBalance(boundary, 105.0))
    after_restart = RevenueAccumulator(path, jst).update(
        AccountBalance(boundary + timedelta(hours=1), 107.0)
    )

    assert at_boundary.daily_usd == 0.0
    assert at_boundary.yesterday_usd == pytest.approx(5.0)
    assert after_restart.daily_usd == pytest.approx(2.0)
    assert after_restart.yesterday_usd == pytest.approx(5.0)


def test_daily_ath_uses_corrected_completed_total_not_incomplete_today(tmp_path):
    jst = ZoneInfo("Asia/Tokyo")
    boundary = datetime(2026, 8, 7, 9, tzinfo=jst)
    accumulator = RevenueAccumulator(tmp_path / "events.json", jst)
    records = RecordsStore(tmp_path / "records.json")
    accumulator.update(AccountBalance(boundary - timedelta(days=1), 100.0))
    records.update(
        accumulator.update(AccountBalance(boundary - timedelta(hours=1), 227.04))
    )

    rollover = accumulator.update(AccountBalance(boundary, 232.34))
    records.update(rollover)
    current = accumulator.update(AccountBalance(boundary + timedelta(hours=1), 400.0))
    records.update(current)

    assert rollover.completed_daily_usd == pytest.approx((132.34,))
    assert current.daily_usd == pytest.approx(167.66)
    assert records.highest()[Period.DAILY] == pytest.approx(132.34)


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


def test_delayed_weekly_reset_requires_balance_drop(tmp_path):
    path = tmp_path / "events.json"
    accumulator = RevenueAccumulator(path, ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    before = datetime(2026, 8, 1, 8, 0, tzinfo=jst)

    accumulator.update(AccountBalance(before, 909.90))
    pending = accumulator.update(AccountBalance(before + timedelta(hours=1), 914.96))
    reset = accumulator.update(AccountBalance(before + timedelta(hours=2), 5.13))
    events = read_json(path, list)

    assert pending.hourly_usd == pytest.approx(5.06)
    assert "completed_weekly_balance" not in events[1]
    assert reset.hourly_usd == pytest.approx(5.13)
    assert reset.completed_weekly_usd == (914.96,)
    assert reset.weekly_usd == 5.13
    # A first-Saturday closure completes the previous payout month; the new
    # payout month starts from the running week only.
    assert reset.monthly_usd == pytest.approx(5.13)
    assert reset.completed_monthly_usd == pytest.approx((914.96,))


def test_payout_month_rollover_excludes_previous_month_weeks(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    for boundary, total in [
        (datetime(2026, 7, 11, 9, tzinfo=jst), 200.0),
        (datetime(2026, 7, 18, 9, tzinfo=jst), 225.0),
        (datetime(2026, 7, 25, 9, tzinfo=jst), 250.0),
    ]:
        accumulator.update(AccountBalance(boundary - timedelta(minutes=5), total))
        accumulator.update(AccountBalance(boundary + timedelta(minutes=1), 1.0))
    accumulator.update(AccountBalance(datetime(2026, 8, 1, 8, 55, tzinfo=jst), 239.96))
    snapshot = accumulator.update(AccountBalance(datetime(2026, 8, 1, 10, tzinfo=jst), 143.09))

    assert snapshot.weekly_usd == pytest.approx(143.09)
    assert snapshot.monthly_usd == pytest.approx(143.09)
    assert snapshot.completed_monthly_usd == pytest.approx((914.96,))


def test_five_week_payout_month_and_restart_keeps_running_values(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    for boundary, total in [
        (datetime(2026, 8, 8, 9, tzinfo=jst), 10.0),
        (datetime(2026, 8, 15, 9, tzinfo=jst), 20.0),
        (datetime(2026, 8, 22, 9, tzinfo=jst), 30.0),
        (datetime(2026, 8, 29, 9, tzinfo=jst), 40.0),
    ]:
        accumulator.update(AccountBalance(boundary - timedelta(minutes=1), total))
        accumulator.update(AccountBalance(boundary + timedelta(minutes=1), 1.0))
    august = accumulator.update(AccountBalance(datetime(2026, 9, 5, 8, 59, tzinfo=jst), 50.0))
    september = accumulator.update(AccountBalance(datetime(2026, 9, 5, 9, 1, tzinfo=jst), 2.0))

    assert august.monthly_usd == pytest.approx(50.0)
    assert september.monthly_usd == pytest.approx(2.0)
    assert september.completed_monthly_usd == pytest.approx((150.0,))


def test_delayed_first_saturday_confirmation_rolls_month_at_confirmation(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("Asia/Tokyo"))
    jst = ZoneInfo("Asia/Tokyo")
    accumulator.update(AccountBalance(datetime(2026, 7, 25, 9, tzinfo=jst), 900.0))
    pending = accumulator.update(AccountBalance(datetime(2026, 8, 1, 9, 30, tzinfo=jst), 914.96))
    reset = accumulator.update(AccountBalance(datetime(2026, 8, 1, 10, tzinfo=jst), 143.09))

    assert pending.monthly_usd == pytest.approx(914.96)
    assert reset.monthly_usd == pytest.approx(143.09)
    assert reset.completed_monthly_usd == pytest.approx((914.96,))


def test_restart_around_rollover_uses_persisted_weekly_closures(tmp_path):
    path = tmp_path / "events.json"
    jst = ZoneInfo("Asia/Tokyo")
    first = RevenueAccumulator(path, jst)
    first.update(AccountBalance(datetime(2026, 8, 1, 8, 59, tzinfo=jst), 914.96))
    second = RevenueAccumulator(path, jst)
    snapshot = second.update(AccountBalance(datetime(2026, 8, 1, 10, tzinfo=jst), 143.09))

    assert snapshot.monthly_usd == pytest.approx(143.09)
    assert snapshot.completed_weekly_usd == pytest.approx((914.96,))
    assert snapshot.completed_monthly_usd == pytest.approx((914.96,))
