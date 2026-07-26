"""Regression tests for fresh-install notification language selection."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).parents[1]
INSTALLER = (ROOT / "install.sh").read_text(encoding="utf-8")


def _function(name: str) -> str:
    match = re.search(
        rf"^{name}\(\) \{{\n.*?^\}}$", INSTALLER, re.MULTILINE | re.DOTALL
    )
    assert match, f"missing {name} function"
    return match.group(0)


FUNCTIONS = "\n".join(
    (
        _function("fail"),
        _function("stdin_is_interactive"),
        _function("select_notification_language"),
    )
)


def _select(stdin: str = "", *, environment: str | None = None, interactive: bool = True):
    env = os.environ.copy()
    env.pop("NOTIFICATION_LANGUAGE", None)
    if environment is not None:
        env["NOTIFICATION_LANGUAGE"] = environment
    result = "return 0" if interactive else "return 1"
    script = (
        f"set -Eeuo pipefail\n{FUNCTIONS}\n"
        f"stdin_is_interactive() {{ {result}; }}\n"
        "select_notification_language\nprintf '%s' \"$NOTIFICATION_LANGUAGE\""
    )
    return subprocess.run(
        ["bash", "-c", script], input=stdin, text=True, capture_output=True, env=env, check=False
    )


def test_fresh_interactive_enter_defaults_to_english():
    result = _select("\n")
    assert result.returncode == 0 and result.stdout == "en"


def test_fresh_interactive_selects_japanese_with_2():
    result = _select("2\n")
    assert result.returncode == 0 and result.stdout == "ja"


def test_fresh_interactive_selects_english_with_1():
    result = _select("1\n")
    assert result.returncode == 0 and result.stdout == "en"


def test_environment_accepts_english_without_prompt():
    result = _select(environment="en")
    assert result.returncode == 0 and result.stdout == "en" and result.stderr == ""


def test_environment_accepts_japanese_without_prompt():
    result = _select(environment="ja")
    assert result.returncode == 0 and result.stdout == "ja" and result.stderr == ""


def test_environment_rejects_invalid_language_without_prompt():
    result = _select(environment="fr")
    assert result.returncode != 0
    assert "NOTIFICATION_LANGUAGE must be en or ja" in result.stderr
    assert "Select Discord" not in result.stderr


def test_noninteractive_unset_language_defaults_to_english():
    result = _select(interactive=False)
    assert result.returncode == 0 and result.stdout == "en" and result.stderr == ""


def test_upgrade_preserves_config_without_language_selection():
    existing, fresh = INSTALLER.rsplit(
        'if [[ -f "${APP_DIR}/config.json" ]]; then', 1
    )[1].split("else", 1)
    assert 'cp -a -- "${APP_DIR}/config.json"' in existing
    assert "select_notification_language" not in existing
    assert "select_notification_language" in fresh
