"""Explicit, evidence-based repair of the delayed-reset corruption."""
from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.utils import read_json, write_json

LOGGER = logging.getLogger(__name__)


def repair_state(config_path: Path, state_dir: Path, apply: bool = False) -> tuple[int, Path | None]:
    """Find known false reset events and optionally correct them atomically."""
    events_path = state_dir / "revenue_events.json"
    if not events_path.exists():
        LOGGER.info("Dry-run: no revenue event file exists; no files changed")
        return 0, None
    events = read_json(events_path, list)
    corrections: list[tuple[int, int]] = []
    ambiguous = 0
    for index in range(1, len(events) - 1):
        event = events[index]
        if "completed_weekly_balance" not in event:
            continue
        balance = float(event.get("balance", 0))
        previous = float(events[index - 1].get("balance", 0))
        if abs(float(event.get("increment", -1)) - balance) > 1e-6 or balance < previous:
            continue
        later = next(
            (candidate for candidate in range(index + 1, len(events))
             if float(events[candidate].get("balance", balance)) < balance),
            None,
        )
        if later is None:
            LOGGER.warning("Ambiguous false reset candidate at %s: no later balance drop", event.get("timestamp"))
            ambiguous += 1
            continue
        corrections.append((index, later))
        LOGGER.info(
            "Correction: false full-balance increment %.2f at %s becomes %.2f; closure moves to %s",
            balance, event.get("timestamp"), max(balance - previous, 0), events[later].get("timestamp"),
        )
    if not apply or not corrections:
        LOGGER.info("Dry-run: %d correction(s), %d ambiguous candidate(s); no files changed", len(corrections), ambiguous)
        return len(corrections), None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = state_dir.parent / f"repair-backup-{stamp}"
    backup.mkdir(mode=0o700)
    shutil.copy2(config_path, backup / "config.json")
    shutil.copytree(state_dir, backup / "state", copy_function=shutil.copy2)
    for false_index, drop_index in corrections:
        false = events[false_index]
        drop = events[drop_index]
        prior_balance = float(events[false_index - 1]["balance"])
        completed = float(false["balance"])
        boundary = false.pop("weekly_boundary", false.get("pending_weekly_boundary"))
        false["increment"] = max(completed - prior_balance, 0.0)
        false.pop("completed_weekly_balance", None)
        if boundary:
            false["pending_weekly_boundary"] = boundary
            drop["weekly_boundary"] = boundary
        drop["completed_weekly_balance"] = completed
        drop["increment"] = float(drop["balance"])
    write_json(events_path, events)
    # Existing derived files may contain corrupt values.  They are backed up;
    # removing them makes normal execution rebuild them without inventing data.
    for name in ("records.json", "history.json"):
        path = state_dir / name
        if path.exists():
            write_json(path, {} if name == "records.json" else [])
    LOGGER.info("Applied %d correction(s). Roll back from %s", len(corrections), backup)
    return len(corrections), backup
