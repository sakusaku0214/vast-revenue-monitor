#!/usr/bin/env python3
"""Command-line entrypoint for Vast Revenue Monitor."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config import AppConfig
from src.logger import configure_logging
from src.scheduler import RevenueMonitor
from src.utils import ensure_directory

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor Vast.ai revenue and post Discord reports."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to config.json",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one report cycle and exit",
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
    monitor = RevenueMonitor(config)
    if args.once:
        monitor.run_once()
    else:
        monitor.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
