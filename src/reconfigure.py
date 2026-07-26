"""Safe interactive post-install configuration editor."""
from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.i18n import normalize_language
from src.utils import write_json


def parse_goal(value: str, current: float) -> float:
    """Parse a finite positive goal, preserving current on empty input."""
    if not value.strip():
        return current
    try:
        goal = float(value)
    except ValueError as exc:
        raise ValueError("Weekly goal must be a number") from exc
    if not math.isfinite(goal) or goal <= 0:
        raise ValueError("Weekly goal must be finite and greater than zero")
    return goal


def select_language(value: str, current: str) -> str:
    """Map an interactive selection, preserving current on empty input."""
    if not value.strip():
        return current
    choices = {"1": "en", "2": "ja", "en": "en", "ja": "ja"}
    if value.strip().lower() not in choices:
        raise ValueError("Language must be 1/en or 2/ja")
    return choices[value.strip().lower()]


def reconfigure(
    path: Path,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], Any] = print,
) -> bool:
    """Interactively update only weekly goal and notification language."""
    original = json.loads(path.read_text(encoding="utf-8"))
    current_goal = float(original.get("weekly_goal_usd", 1000.0))
    current_language = normalize_language(original.get("language", "en"))
    output_fn("Vast Revenue Monitor Reconfiguration")
    goal_prompt = f"Current weekly goal: ${current_goal:,.2f}\nNew goal [keep]: "
    goal = parse_goal(input_fn(goal_prompt), current_goal)
    output_fn("Select notification language: 1) English  2) 日本語")
    language_prompt = f"Current language: {current_language} [keep]: "
    language = select_language(input_fn(language_prompt), current_language)
    output_fn(f"Weekly goal: ${current_goal:,.2f} -> ${goal:,.2f}")
    output_fn(f"Notification language: {current_language} -> {language}")
    if input_fn("Apply these changes? [y/N]: ").strip().lower() != "y":
        output_fn("No changes applied.")
        return False
    updated = dict(original)
    updated["weekly_goal_usd"] = goal
    updated["language"] = language
    write_json(path, updated)
    output_fn("Configuration updated successfully.")
    return True


def main() -> int:
    return 0 if reconfigure(Path("/opt/vast-revenue-monitor/config.json")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
