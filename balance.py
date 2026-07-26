#!/usr/bin/env python3
"""Command-line entrypoint for Vast Revenue Monitor."""
from __future__ import annotations

import argparse
import fcntl
import logging
from pathlib import Path

from src.config import AppConfig
from src.logger import configure_logging
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
    return parser.parse_args()


def main() -> int:
    """Run the monitor."""
    args = parse_args()
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
        monitor = RevenueMonitor(config)
        if args.validate:
            monitor.validate_connections()
        elif args.once:
            monitor.run_once()
        else:
            monitor.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
