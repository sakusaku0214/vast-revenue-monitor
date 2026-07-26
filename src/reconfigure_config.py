"""Safe interactive updater for the supported mutable settings."""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    """Durably replace *path* without exposing a partially written file."""
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".config.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o640)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main(path: Path) -> int:
    """Prompt for, validate, review, and atomically apply supported changes."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("configuration root must be a JSON object")
        current_goal = float(data.get("weekly_goal_usd", 1000.0))
        if not math.isfinite(current_goal) or current_goal <= 0:
            raise ValueError("current weekly goal must be a positive finite number")
        current_language = data.get("language", "en")
        if current_language not in {"en", "ja"}:
            current_language = "en"
        current_detailed_report = data.get("detailed_report", False)
        if not isinstance(current_detailed_report, bool):
            raise ValueError("current detailed report setting must be true or false")

        print(f"Current weekly goal: ${current_goal:g}")
        print(f"Current notification language: {current_language}")
        print(
            "Current detailed report: "
            f"{'enabled' if current_detailed_report else 'disabled'}"
        )
        raw_goal = input(f"Weekly revenue goal (USD) [{current_goal:g}]: ").strip()
        goal = current_goal if not raw_goal else float(raw_goal)
        if not math.isfinite(goal) or goal <= 0:
            raise ValueError("weekly goal must be a positive finite number")

        print("Select Discord notification language:\n1) English\n2) 日本語")
        choice = input(f"Choice [{current_language}]: ").strip().lower()
        language = current_language
        if choice:
            language = {"1": "en", "en": "en", "2": "ja", "ja": "ja"}.get(
                choice, ""
            )
        if language not in {"en", "ja"}:
            raise ValueError("language must be en or ja")

        print("Detailed report:\n1) Disabled (compact report)\n2) Enabled (detailed report)")
        detailed_report = current_detailed_report
        while True:
            choice = input(
                "Choice "
                f"[{'enabled' if current_detailed_report else 'disabled'}]: "
            ).strip().lower()
            if not choice:
                break
            if choice in {"1", "false", "no", "n", "off"}:
                detailed_report = False
                break
            if choice in {"2", "true", "yes", "y", "on"}:
                detailed_report = True
                break
            print("Invalid choice. Enter 1/2, true/false, yes/no, y/n, or on/off.")

        print("\nProposed changes:")
        print(f"  Weekly goal:        {goal:g}")
        print(f"  Language:           {language}")
        print(f"  Detailed report:    {'enabled' if detailed_report else 'disabled'}")
        if input("Apply these changes? [y/N]: ").strip().lower() not in {"y", "yes"}:
            print("No changes applied.")
            return 3

        updated = dict(data)
        updated["weekly_goal_usd"] = goal
        updated["language"] = language
        updated["detailed_report"] = detailed_report
        if updated == data:
            print("Configuration is unchanged.")
            return 3
        _atomic_write(path, updated)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Configuration was not changed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
