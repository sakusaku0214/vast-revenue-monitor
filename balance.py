#!/usr/bin/env python3
"""Command-line entrypoint for Vast Revenue Monitor."""
from __future__ import annotations

import argparse
import fcntl
import logging
from pathlib import Path

from src.config import AppConfig
from src.logger import configure_logging
from src.repair import repair_state
from src.scheduler import RevenueMonitor
from src.utils import ensure_directory
from src.version import VERSION

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor Vast.ai revenue and post Discord reports."
    )
    parser.add_argument("--version", action="version", version=f"Vast Revenue Monitor {VERSION}")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to config.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once",
        action="store_true",
        help="Run one report cycle and exit",
    )
    mode.add_argument(
        "--validate",
        action="store_true",
        help="Validate Vast.ai and exchange APIs without sending a report",
    )
    mode.add_argument(
        "--repair-state",
        action="store_true",
        help="Inspect state for known delayed-reset corruption (dry-run by default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply --repair-state corrections after creating a backup",
    )
    return parser.parse_args()


def main() -> int:
    """Run the monitor."""
    args = parse_args()
    if args.apply and not args.repair_state:
        raise ValueError("--apply is only valid with --repair-state")
    # Keep every config-relative operation independent of the caller's cwd.
    args.config = args.config.expanduser().resolve()
    config = AppConfig.load(args.config)
    ensure_directory(config.state_dir)
    ensure_directory(config.log_dir)
    configure_logging(config.log_dir, config.log_level)
    LOGGER.info("Starting Vast Revenue Monitor")
    lock_path = config.state_dir / "monitor.lock"
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another Vast Revenue Monitor process is running") from exc
        if args.repair_state:
            repair_state(args.config, config.state_dir, args.apply)
        elif args.validate:
            monitor = RevenueMonitor(config)
            monitor.validate_connections()
        elif args.once:
            monitor = RevenueMonitor(config)
            monitor.run_once()
        else:
            monitor = RevenueMonitor(config)
            monitor.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
