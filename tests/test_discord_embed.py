from __future__ import annotations

from datetime import datetime, timezone

from src import discord_embed
from src.discord_embed import DiscordNotifier
from src.models import Change, GoalStatus, GpuAvailability, Period, ReportStatus, RevenueSnapshot


def test_report_status_warns_when_all_gpus_are_available():
    notifier = DiscordNotifier("https://example.invalid", 1)
    snapshot = RevenueSnapshot(
        datetime(2026, 7, 25, tzinfo=timezone.utc),
        1.0,
        2.0,
        3.0,
        4.0,
        GpuAvailability(total=4, rented=0),
    )
    goal = GoalStatus(2, 118, 1, 1, 0, 48, True, snapshot.timestamp, snapshot.timestamp)

    assert notifier._report_status(snapshot, {}, goal) is ReportStatus.WARNING


def test_embed_contains_gpu_warning_and_jpy_format():
    notifier = DiscordNotifier("https://example.invalid", 1)
    snapshot = RevenueSnapshot(
        datetime(2026, 7, 25, tzinfo=timezone.utc),
        8.0,
        8.0,
        8.0,
        8.0,
        GpuAvailability(total=2, rented=0),
    )
    changes = {period.value: Change(1.0, 10.0) for period in Period}
    goal = GoalStatus(8, 112, 6, 5, 1, 130, True, snapshot.timestamp, snapshot.timestamp)

    embed = notifier._embed(snapshot, 154.25, changes, {}, goal, ReportStatus.WARNING)
    values = "\n".join(str(field["value"]) for field in embed["fields"])
    names = "\n".join(str(field["name"]) for field in embed["fields"])

    assert "¥1,234" in values
    assert "All GPUs Available" in names


def test_validate_webhook_uses_get_without_posting(monkeypatch):
    calls = {"get": 0, "post": 0, "response_closed": 0, "session_closed": 0}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"name": "Revenue reports"}

        def close(self):
            calls["response_closed"] += 1

    class Session:
        def mount(self, *_args, **_kwargs):
            return None

        def get(self, *_args, **_kwargs):
            calls["get"] += 1
            return Response()

        def post(self, *_args, **_kwargs):
            calls["post"] += 1
            raise AssertionError("validation must not post")

        def close(self):
            calls["session_closed"] += 1

    monkeypatch.setattr(discord_embed.requests, "Session", Session)

    DiscordNotifier("https://discord.com/api/webhooks/id/token", 5).validate_webhook()

    assert calls == {
        "get": 1,
        "post": 0,
        "response_closed": 1,
        "session_closed": 1,
    }
