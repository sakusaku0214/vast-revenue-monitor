from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.weekly_reset import WeeklyResetLearner
from src.utils import read_json, write_json

JST = ZoneInfo("Asia/Tokyo")


def test_weekly_reset_requires_all_confidence_conditions(tmp_path):
    learner = WeeklyResetLearner(tmp_path / "weekly_reset.json", JST)
    now = datetime(2026, 7, 25, 9, 2, tzinfo=JST)

    assert learner.observe(40.0, 1.0, now) is False
    assert learner.observe(100.0, 4.0, now) is False
    assert learner.observe(100.0, 20.0, now) is False
    assert learner.observe(100.0, 2.0, now) is True


def test_weekly_reset_uses_last_full_scan_interval(tmp_path):
    path = tmp_path / "weekly_reset.json"
    write_json(path, {
        "learned_time": "09:02:00",
        "last_reset_timestamp": "2026-07-25T09:02:00+09:00",
        "last_full_scan": "2026-07-25",
        "observations": 1,
    })
    learner = WeeklyResetLearner(path, JST)

    narrow = datetime(2026, 8, 1, 9, 2, tzinfo=JST)
    wide_only = datetime(2026, 8, 1, 8, 40, tzinfo=JST)
    four_weeks_later = datetime(2026, 8, 22, 8, 40, tzinfo=JST)

    assert learner.should_monitor(narrow) is True
    assert learner.should_monitor(wide_only) is False
    assert learner.should_monitor(four_weeks_later) is True


def test_weekly_reset_stores_last_full_scan_on_wide_detection(tmp_path):
    path = tmp_path / "weekly_reset.json"
    learner = WeeklyResetLearner(path, JST)

    assert learner.observe(100.0, 1.0, datetime(2026, 7, 25, 8, 40, tzinfo=JST))
    state = read_json(path, lambda: {})

    assert state["last_full_scan"] == "2026-07-25"
