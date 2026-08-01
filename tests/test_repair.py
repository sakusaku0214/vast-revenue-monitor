from __future__ import annotations

import json

import pytest

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
