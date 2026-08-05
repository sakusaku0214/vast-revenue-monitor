from __future__ import annotations

import json

import pytest

import balance
from src.repair import repair_state


def _write_fixture(tmp_path):
    config = tmp_path / "config.json"
    state = tmp_path / "state"
    state.mkdir()
    config.write_text('{"secret":"test-only"}\n', encoding="utf-8")
    events = [
        {"timestamp": "2026-08-01T08:00:00+09:00", "balance": 909.90, "increment": 5.19},
        {"timestamp": "2026-08-01T09:00:00+09:00", "balance": 914.96, "increment": 914.96,
         "completed_weekly_balance": 909.90, "weekly_boundary": "2026-08-01T09:00:00+09:00"},
        {"timestamp": "2026-08-01T10:00:00+09:00", "balance": 5.13, "increment": 0.0},
    ]
    (state / "revenue_events.json").write_text(json.dumps(events), encoding="utf-8")
    return config, state


def test_repair_dry_run_does_not_change_files(tmp_path):
    config, state = _write_fixture(tmp_path)
    before = (state / "revenue_events.json").read_bytes()
    count, backup = repair_state(config, state)
    assert count == 1 and backup is None
    assert (state / "revenue_events.json").read_bytes() == before


def test_repair_apply_backs_up_and_moves_closure(tmp_path):
    config, state = _write_fixture(tmp_path)
    count, backup = repair_state(config, state, apply=True)
    events = json.loads((state / "revenue_events.json").read_text())
    assert count == 1 and backup is not None
    assert (backup / "config.json").exists()
    assert (backup / "state" / "revenue_events.json").exists()
    assert events[1]["increment"] == pytest.approx(5.06)
    assert "completed_weekly_balance" not in events[1]
    assert events[2]["completed_weekly_balance"] == 914.96
    assert events[2]["increment"] == 5.13


def test_ambiguous_repair_is_unchanged(tmp_path):
    config, state = _write_fixture(tmp_path)
    events_path = state / "revenue_events.json"
    events = json.loads(events_path.read_text())[:2]
    events_path.write_text(json.dumps(events), encoding="utf-8")
    before = events_path.read_bytes()
    count, backup = repair_state(config, state, apply=True)
    assert count == 0 and backup is None
    assert events_path.read_bytes() == before


def test_repair_completed_period_ath_only_when_applied(tmp_path):
    config, state = _write_fixture(tmp_path)
    events_path = state / "revenue_events.json"
    events = json.loads(events_path.read_text())
    # Make the only retained day and week unambiguously completed.
    events.append({
        "timestamp": "2026-08-08T10:00:00+09:00", "balance": 3.0,
        "increment": 3.0, "completed_weekly_balance": 5.13,
        "weekly_boundary": "2026-08-08T09:00:00+09:00",
    })
    events_path.write_text(json.dumps(events), encoding="utf-8")
    records_path = state / "records.json"
    records_path.write_text(json.dumps({
        "hourly": {"amount_usd": 9.0, "timestamp": "old"},
        "daily": {"amount_usd": 999.0, "timestamp": "old"},
        "weekly": {"amount_usd": 999.0, "timestamp": "old"},
        "monthly": {"amount_usd": 999.0, "timestamp": "old"},
    }), encoding="utf-8")
    before = records_path.read_bytes()

    count, backup = repair_state(config, state)
    assert count >= 3 and backup is None
    assert records_path.read_bytes() == before

    count, backup = repair_state(config, state, apply=True)
    repaired = json.loads(records_path.read_text())
    assert count >= 3 and backup is not None
    assert (backup / "state" / "records.json").read_bytes() == before
    assert repaired["hourly"]["amount_usd"] == pytest.approx(5.19)
    assert repaired["hourly"]["timestamp"] == events[0]["timestamp"]
    assert repaired["daily"]["amount_usd"] != 999.0
    assert repaired["weekly"]["amount_usd"] != 999.0
    assert repaired["monthly"]["amount_usd"] != 999.0


def test_hourly_uses_corrected_increments_never_balances(tmp_path, caplog):
    caplog.set_level("INFO", logger="src.repair")
    config, state = _write_fixture(tmp_path)
    events_path = state / "revenue_events.json"
    events = json.loads(events_path.read_text())
    events.insert(1, {
        "timestamp": "2026-08-01T08:30:00+09:00", "balance": 911.51,
        "increment": 11.61,
    })
    events_path.write_text(json.dumps(events), encoding="utf-8")
    records_path = state / "records.json"
    records_path.write_text(json.dumps({
        "hourly": {"amount_usd": 914.96, "timestamp": "bad"},
    }), encoding="utf-8")
    before = records_path.read_bytes()

    count, backup = repair_state(config, state)

    assert count == 2 and backup is None
    assert records_path.read_bytes() == before
    assert "invalid hourly ATH 914.96 becomes 11.61" in caplog.text

    repair_state(config, state, apply=True)
    repaired = json.loads(records_path.read_text())
    assert repaired["hourly"] == {
        "amount_usd": 11.61,
        "timestamp": "2026-08-01T08:30:00+09:00",
    }
    assert repaired["hourly"]["amount_usd"] != max(event["balance"] for event in events)


def test_hourly_without_positive_evidence_is_preserved(tmp_path, caplog):
    config, state = _write_fixture(tmp_path)
    (state / "revenue_events.json").write_text(json.dumps([
        {"timestamp": "2026-08-01T08:00:00+09:00", "balance": 10, "increment": 0},
        {"timestamp": "2026-08-01T09:00:00+09:00", "balance": 9, "increment": -1},
    ]), encoding="utf-8")
    records_path = state / "records.json"
    records_path.write_text(json.dumps({
        "hourly": {"amount_usd": 7.0, "timestamp": "preserved"},
    }), encoding="utf-8")

    count, backup = repair_state(config, state, apply=True)

    assert count == 0 and backup is None
    assert json.loads(records_path.read_text())["hourly"]["amount_usd"] == 7.0
    assert "cannot be reconstructed" in caplog.text


def test_cli_repair_finds_config_relative_state_from_unrelated_cwd(
    tmp_path, monkeypatch, caplog
):
    install = tmp_path / "opt" / "vast-revenue-monitor"
    install.mkdir(parents=True)
    config, fixture_state = _write_fixture(tmp_path)
    config.replace(install / "config.json")
    fixture_state.replace(install / "state")
    (install / "logs").mkdir()
    (install / "config.json").write_text(json.dumps({
        "discord_webhook_url": "https://discord.com/api/webhooks/id/token",
        "vast_api_key": "secret", "state_dir": "state", "log_dir": "logs",
    }), encoding="utf-8")
    unrelated = tmp_path / "home" / "sakusaku"
    unrelated.mkdir(parents=True)
    monkeypatch.chdir(unrelated)
    monkeypatch.setattr("sys.argv", ["balance.py", "--config", str(install / "config.json"), "--repair-state"])

    assert balance.main() == 0
    assert (install / "state" / "monitor.lock").exists()
    assert not (unrelated / "state").exists()


def test_repair_dry_run_identifies_zero_monthly_ath_when_completed_month_exists(tmp_path, caplog):
    caplog.set_level("INFO", logger="src.repair")
    config = tmp_path / "config.json"
    state = tmp_path / "state"
    state.mkdir()
    config.write_text('{"secret":"test-only"}\n', encoding="utf-8")
    events = [
        {"timestamp": "2026-07-25T08:59:00+09:00", "balance": 900.0, "increment": 10.0},
        {"timestamp": "2026-08-01T10:00:00+09:00", "balance": 143.09, "increment": 143.09,
         "completed_weekly_balance": 914.96, "weekly_boundary": "2026-08-01T09:00:00+09:00"},
    ]
    (state / "revenue_events.json").write_text(json.dumps(events), encoding="utf-8")
    records_path = state / "records.json"
    records_path.write_text(json.dumps({
        "monthly": {"amount_usd": 0.0, "timestamp": "bad"},
    }), encoding="utf-8")
    before = records_path.read_bytes()

    count, backup = repair_state(config, state)

    assert count == 1 and backup is None
    assert records_path.read_bytes() == before
    assert "invalid monthly ATH 0.00 becomes 914.96" in caplog.text


def test_repair_apply_backs_up_and_repairs_monthly_ath(tmp_path):
    config = tmp_path / "config.json"
    state = tmp_path / "state"
    state.mkdir()
    config.write_text('{"secret":"test-only"}\n', encoding="utf-8")
    (state / "revenue_events.json").write_text(json.dumps([
        {"timestamp": "2026-08-01T10:00:00+09:00", "balance": 143.09, "increment": 143.09,
         "completed_weekly_balance": 914.96, "weekly_boundary": "2026-08-01T09:00:00+09:00"},
    ]), encoding="utf-8")
    records_path = state / "records.json"
    records_path.write_text(json.dumps({"monthly": {"amount_usd": 0.0, "timestamp": "bad"}}), encoding="utf-8")

    count, backup = repair_state(config, state, apply=True)
    repaired = json.loads(records_path.read_text())

    assert count == 1 and backup is not None
    assert (backup / "state" / "records.json").exists()
    assert repaired["monthly"]["amount_usd"] == pytest.approx(914.96)
