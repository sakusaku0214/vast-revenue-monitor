"""Explicit, evidence-based repair of the delayed-reset corruption."""
from __future__ import annotations

import logging
import math
import shutil
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.utils import read_json, write_json

LOGGER = logging.getLogger(__name__)
JST = ZoneInfo("Asia/Tokyo")


def _hourly_ath(events: list[dict[str, object]]) -> tuple[float, object] | None:
    """Return the largest evidenced positive interval and its event timestamp."""
    candidates: list[tuple[float, object]] = []
    for event in events:
        try:
            increment = float(event["increment"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(increment) and increment > 0 and event.get("timestamp"):
            candidates.append((increment, event["timestamp"]))
    return max(candidates, key=lambda candidate: candidate[0]) if candidates else None


def _completed_ath(events: list[dict[str, object]]) -> dict[str, float]:
    """Rebuild completed-period records from the retained event evidence."""
    if not events:
        return {period: 0.0 for period in ("daily", "weekly", "monthly")}
    latest = datetime.fromisoformat(str(events[-1]["timestamp"])).astimezone(JST)
    latest_start = datetime.combine(latest.date(), time(9), tzinfo=JST)
    if latest < latest_start:
        latest_start -= timedelta(days=1)
    daily: dict[datetime, float] = {}
    for event in events:
        observed = datetime.fromisoformat(str(event["timestamp"])).astimezone(JST)
        start = datetime.combine(observed.date(), time(9), tzinfo=JST)
        if observed < start:
            start -= timedelta(days=1)
        if start < latest_start:
            daily[start] = daily.get(start, 0.0) + float(event.get("increment", 0.0))

    weekly: list[float] = []
    monthly: dict[tuple[int, int], float] = {}
    for event in events:
        if "completed_weekly_balance" not in event:
            continue
        amount = float(event["completed_weekly_balance"])
        weekly.append(amount)
        boundary = datetime.fromisoformat(
            str(event.get("weekly_boundary", event["timestamp"]))
        ).astimezone(JST)
        key = (boundary.year, boundary.month)
        monthly[key] = monthly.get(key, 0.0) + amount
    week_start = latest_start - timedelta(days=(latest_start.weekday() - 5) % 7)
    running_month_end = week_start + timedelta(days=7)
    current_month = (running_month_end.year, running_month_end.month)
    completed_months = [value for key, value in monthly.items() if key != current_month]
    return {
        "daily": max(daily.values(), default=0.0),
        "weekly": max(weekly, default=0.0),
        "monthly": max(completed_months, default=0.0),
    }


def _move_false_closures(
    events: list[dict[str, object]], corrections: list[tuple[int, int]]
) -> None:
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
    repaired_events = deepcopy(events)
    _move_false_closures(repaired_events, corrections)
    records_path = state_dir / "records.json"
    records = read_json(records_path, dict) if records_path.exists() else {}
    expected = _completed_ath(repaired_events)
    expected_timestamps: dict[str, object] = {}
    hourly = None if ambiguous else _hourly_ath(repaired_events)
    if ambiguous:
        LOGGER.warning(
            "Hourly ATH cannot be reconstructed while delayed-reset evidence is ambiguous; "
            "stored value will remain unchanged"
        )
    elif hourly is None:
        LOGGER.warning(
            "Hourly ATH cannot be reconstructed: no valid positive increment evidence; "
            "stored value will remain unchanged"
        )
    else:
        expected["hourly"], expected_timestamps["hourly"] = hourly
    invalid_ath = [
        period for period, amount in expected.items()
        if period in records
        and abs(float(records[period].get("amount_usd", 0.0)) - amount) > 1e-6
    ]
    for period in invalid_ath:
        LOGGER.info(
            "Correction: invalid %s ATH %.2f becomes %.2f",
            period, float(records[period]["amount_usd"]), expected[period],
        )
    correction_count = len(corrections) + len(invalid_ath)
    if not apply or not correction_count:
        LOGGER.info(
            "Dry-run: %d correction(s), %d ambiguous candidate(s); no files changed",
            correction_count, ambiguous,
        )
        return correction_count, None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = state_dir.parent / f"repair-backup-{stamp}"
    backup.mkdir(mode=0o700)
    shutil.copy2(config_path, backup / "config.json")
    shutil.copytree(state_dir, backup / "state", copy_function=shutil.copy2)
    write_json(events_path, repaired_events)
    if invalid_ath:
        stamp_value = events[-1]["timestamp"]
        for period in invalid_ath:
            records[period] = {
                "amount_usd": expected[period],
                "timestamp": expected_timestamps.get(period, stamp_value),
            }
        write_json(records_path, records)
    # Reset history only when event increments changed; ATH repair alone does
    # not invalidate the displayed historical snapshots.
    history_path = state_dir / "history.json"
    if corrections and history_path.exists():
        write_json(history_path, [])
    LOGGER.info("Applied %d correction(s). Roll back from %s", correction_count, backup)
    return correction_count, backup
