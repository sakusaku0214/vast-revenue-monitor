import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.config import AppConfig
from src.discord_embed import DiscordNotifier
from src.i18n import CATALOG
from src.models import AccountBalance, Change, GoalStatus, Period, ReportStatus, RevenueSnapshot
from src.revenue import RevenueAccumulator


@pytest.mark.parametrize("gap", [timedelta(minutes=15), timedelta(hours=1), timedelta(hours=3)])
def test_hourly_is_actual_latest_interval_for_any_gap(tmp_path, gap):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("UTC"))
    start = datetime(2026, 7, 26, 1, 0, 1, tzinfo=timezone.utc)
    accumulator.update(AccountBalance(start, 10))
    result = accumulator.update(AccountBalance(start + gap, 13.56739328))
    assert result.hourly_usd == pytest.approx(3.56739328)


def test_samples_59_59_apart_are_not_summed_and_periods_still_aggregate(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("UTC"))
    first = datetime(2026, 7, 26, 1, 0, 1, tzinfo=timezone.utc)
    accumulator.update(AccountBalance(first - timedelta(hours=1), 20))
    one = accumulator.update(AccountBalance(first, 23.56739328))
    two = accumulator.update(AccountBalance(first + timedelta(minutes=59, seconds=59), 28.92604038))
    assert one.hourly_usd == pytest.approx(3.56739328)
    assert two.hourly_usd == pytest.approx(5.35864710)
    assert two.daily_usd == pytest.approx(8.92604038)
    # Monthly contains completed weekly closures, not in-progress deltas.
    assert two.monthly_usd == 0
    assert two.weekly_usd == pytest.approx(28.92604038)


def test_missing_zero_and_negative_movements_are_zero(tmp_path):
    accumulator = RevenueAccumulator(tmp_path / "events.json", ZoneInfo("UTC"))
    now = datetime(2026, 7, 26, tzinfo=timezone.utc)
    assert accumulator.update(AccountBalance(now, 5)).hourly_usd == 0
    assert accumulator.update(AccountBalance(now + timedelta(minutes=1), 5)).hourly_usd == 0
    assert accumulator.update(AccountBalance(now + timedelta(minutes=2), 4)).hourly_usd == 0


def _embed(language="en", weekly=95, goal_value=100):
    notifier = DiscordNotifier("https://example.invalid", 1, goal_value, False, "UTC", language)
    timestamp = datetime(2026, 7, 26, tzinfo=timezone.utc)
    snapshot = RevenueSnapshot(timestamp, 5.36, 20, weekly, 50)
    changes = {p.value: Change(0, 0) for p in Period}
    goal = GoalStatus(1, 1, 1, 1, 0, 1, True, timestamp, timestamp)
    return notifier._embed(snapshot, 150, changes, {}, goal, ReportStatus.NORMAL)


def test_translation_parity_and_labels_and_embed_limits():
    assert CATALOG["en"].keys() == CATALOG["ja"].keys()
    english, japanese = _embed("en"), _embed("ja")
    assert "Hourly" in english["fields"][0]["value"]
    assert "Remaining to Goal: $5.00" in english["fields"][1]["value"]
    assert "直近区間" in japanese["fields"][0]["value"]
    assert "目標まで残り" in japanese["fields"][1]["value"]
    for embed in (english, japanese):
        assert len(embed["title"]) <= 256
        assert len(embed["fields"]) <= 25
        assert sum(len(f["name"]) + len(f["value"]) for f in embed["fields"]) < 6000


def test_remaining_is_clamped():
    assert "Remaining to Goal: $0.00" in _embed("en", 150)["fields"][1]["value"]


def test_config_language_default_and_fallback(tmp_path, caplog):
    valid_config = {
        "discord_webhook_url": "https://discord.com/api/webhooks/1/token",
        "vast_api_key": "secret",
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(valid_config))
    assert AppConfig.load(path).language == "en"
    valid_config["language"] = "xx"
    path.write_text(json.dumps(valid_config))
    assert AppConfig.load(path).language == "en"
    assert "falling back" in caplog.text
