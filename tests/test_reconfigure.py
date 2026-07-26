import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src import reconfigure_config


SCRIPT = Path(__file__).parents[1] / "reconfigure.sh"


def run_reconfigure(path, answers):
    env = {
        **os.environ,
        "ALLOW_NON_ROOT": "1",
        "SKIP_SERVICE_RESTART": "1",
        "APP_DIR": str(SCRIPT.parent),
        "CONFIG_PATH": str(path),
        "PYTHON": sys.executable,
    }
    return subprocess.run([str(SCRIPT)], input=answers, text=True, capture_output=True, env=env, check=False)


def config():
    return {"weekly_goal_usd": 1000, "language": "en", "vast_api_key": "TOP_SECRET", "discord_webhook_url": "https://discord.com/api/webhooks/SECRET", "unknown": {"keep": True}}


def test_reconfigure_en_to_ja_preserves_secrets_and_unknown_keys(tmp_path):
    path = tmp_path / "config.json"; path.write_text(json.dumps(config()))
    result = run_reconfigure(path, "1234.5\n2\ny\n")
    assert result.returncode == 0
    updated = json.loads(path.read_text())
    assert updated["weekly_goal_usd"] == 1234.5 and updated["language"] == "ja"
    assert updated["vast_api_key"] == "TOP_SECRET" and updated["unknown"] == {"keep": True}
    assert "TOP_SECRET" not in result.stdout + result.stderr and "webhooks/SECRET" not in result.stdout + result.stderr


def test_reconfigure_enter_preserves_values_and_ja_to_en(tmp_path):
    value = config(); value["language"] = "ja"
    path = tmp_path / "config.json"; path.write_text(json.dumps(value))
    assert run_reconfigure(path, "\n1\ny\n").returncode == 0
    updated = json.loads(path.read_text())
    assert updated["weekly_goal_usd"] == 1000 and updated["language"] == "en"


def test_invalid_goals_leave_original_untouched(tmp_path):
    for invalid in ("0", "-1", "nan", "inf", "bad"):
        path = tmp_path / f"{invalid}.json"; original = json.dumps(config()); path.write_text(original)
        result = run_reconfigure(path, invalid + "\n")
        assert result.returncode == 2 and path.read_text() == original


def test_atomic_replace_failure_leaves_original_usable(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    original = json.dumps(config())
    path.write_text(original)

    def fail_replace(_source, _destination):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(reconfigure_config.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        reconfigure_config._atomic_write(path, {"weekly_goal_usd": 2, "language": "ja"})

    assert path.read_text() == original
    assert json.loads(path.read_text()) == config()
