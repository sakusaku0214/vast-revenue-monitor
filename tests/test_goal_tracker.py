from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.goal_tracker import GoalTracker


def test_goal_tracker_reports_expected_progress_and_pace(tmp_path):
    tracker = GoalTracker(tmp_path / "goal.json", ZoneInfo("Asia/Tokyo"), 120.0)
    now = datetime(2026, 7, 24, 21, 0, tzinfo=ZoneInfo("Asia/Tokyo"))

    status = tracker.calculate(now, 60.0)

    assert status.current_percent == 50.0
    assert status.expected_percent == 50.0
    assert status.pace_delta_percent == 0.0
    assert status.on_track is True


def test_goal_tracker_uses_previous_business_day_before_0900(tmp_path):
    tracker = GoalTracker(tmp_path / "goal.json", ZoneInfo("Asia/Tokyo"), 120.0)
    now = datetime(2026, 7, 25, 8, 0, tzinfo=ZoneInfo("Asia/Tokyo"))

    status = tracker.calculate(now, 100.0)

    assert status.business_day_start.day == 24
    assert status.business_day_end.day == 25
    assert status.expected_percent > 95.0
