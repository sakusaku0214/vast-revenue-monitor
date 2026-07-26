"""Regression tests for fresh-install notification language selection."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


INSTALLER = Path(__file__).parents[1] / "install.sh"


def select_language(*, value: str | None = None, answer: str = "", interactive: bool):
    environment = {**os.environ, "VAST_INSTALLER_LIBRARY_ONLY": "true"}
    if value is None:
        environment.pop("NOTIFICATION_LANGUAGE", None)
    else:
        environment["NOTIFICATION_LANGUAGE"] = value
    command = (
        f'source "{INSTALLER}"; '
        f'select_notification_language {str(interactive).lower()}; '
        'printf "RESULT=%s\\n" "$NOTIFICATION_LANGUAGE"'
    )
    return subprocess.run(
        ["bash", "-c", command],
        input=answer,
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("\n", "en"), ("1\n", "en"), ("en\n", "en"), ("2\n", "ja"), ("ja\n", "ja")],
)
def test_fresh_interactive_language_choices(answer, expected):
    result = select_language(answer=answer, interactive=True)
    assert result.returncode == 0
    assert f"RESULT={expected}" in result.stdout


@pytest.mark.parametrize("language", ["en", "ja"])
def test_environment_language_is_accepted_without_prompt(language):
    result = select_language(value=language, answer="ignored\n", interactive=True)
    assert result.returncode == 0
    assert f"RESULT={language}" in result.stdout
    assert "Select Discord notification language" not in result.stdout


def test_invalid_environment_language_is_rejected():
    result = select_language(value="fr", interactive=True)
    assert result.returncode != 0
    assert "NOTIFICATION_LANGUAGE must be en or ja" in result.stderr


def test_noninteractive_unset_language_defaults_to_english():
    result = select_language(interactive=False)
    assert result.returncode == 0
    assert "RESULT=en" in result.stdout
    assert "Select Discord notification language" not in result.stdout


def test_upgrade_preserves_config_without_calling_language_selector():
    source = INSTALLER.read_text(encoding="utf-8")
    preserve = source.index('if [[ -f "${APP_DIR}/config.json" ]]')
    first_install = source.index("select_notification_language true")
    else_branch = source.rfind("else", preserve, first_install)
    assert preserve < else_branch < first_install
    assert 'cp -a -- "${APP_DIR}/config.json" "${STAGING_DIR}/config.json"' in source[
        preserve:else_branch
    ]
