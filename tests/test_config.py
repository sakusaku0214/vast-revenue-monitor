from __future__ import annotations

import json

import pytest

from src.config import AppConfig


def _write_config(path, **overrides):
    data = {
        "discord_webhook_url": "https://discord.com/api/webhooks/id/token",
        "vast_api_key": "secret",
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_config_rejects_placeholder_credentials(tmp_path):
    path = tmp_path / "config.json"
    _write_config(path, vast_api_key="REPLACE_ME")

    with pytest.raises(ValueError, match="Replace the example"):
        AppConfig.load(path)


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("daily_goal_usd", 0),
        ("request_timeout_seconds", 0),
        ("exchange_timeout_seconds", 301),
        ("log_level", "verbose"),
        ("vast_base_url", "http://example.com"),
    ],
)
def test_config_rejects_unsafe_values(tmp_path, setting, value):
    path = tmp_path / "config.json"
    _write_config(path, **{setting: value})

    with pytest.raises(ValueError):
        AppConfig.load(path)


def test_config_accepts_valid_minimal_file(tmp_path):
    path = tmp_path / "config.json"
    _write_config(path)

    config = AppConfig.load(path)

    assert config.daily_goal_usd == 120.0
    assert config.weekly_goal_usd == 1000.0
    assert config.detailed_report is False
    assert len(config.exchange.urls) == 3
    assert config.vast.revenue_endpoint == "/users/current/"
    assert config.vast.auth_mode == "query"
    assert config.vast.balance_field == "balance"
    assert config.state_dir == tmp_path / "state"
    assert config.log_dir == tmp_path / "logs"


def test_relative_directories_are_based_on_config_not_cwd(tmp_path, monkeypatch):
    install = tmp_path / "opt" / "vast-revenue-monitor"
    install.mkdir(parents=True)
    path = install / "config.json"
    _write_config(path, state_dir="var/state", log_dir="var/log")
    unrelated = tmp_path / "home" / "caller"
    unrelated.mkdir(parents=True)
    monkeypatch.chdir(unrelated)

    config = AppConfig.load(path)

    assert config.state_dir == install / "var" / "state"
    assert config.log_dir == install / "var" / "log"


def test_absolute_directories_remain_unchanged(tmp_path):
    path = tmp_path / "config.json"
    state = tmp_path / "absolute-state"
    logs = tmp_path / "absolute-logs"
    _write_config(path, state_dir=str(state), log_dir=str(logs))

    config = AppConfig.load(path)

    assert config.state_dir == state
    assert config.log_dir == logs
