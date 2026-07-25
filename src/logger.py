"""Logging setup."""
from __future__ import annotations

import gzip
import logging
import shutil
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from src.utils import ensure_directory


class GZipTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Daily rotating log handler that compresses rotated files."""

    def getFilesToDelete(self) -> list[str]:
        """Return compressed backups beyond the configured retention count."""
        log_path = Path(self.baseFilename)
        candidates = sorted(log_path.parent.glob(f"{log_path.name}.*.gz"))
        if len(candidates) <= self.backupCount:
            return []
        return [str(path) for path in candidates[: len(candidates) - self.backupCount]]

    def rotate(self, source: str, dest: str) -> None:
        """Compress rotated log output with gzip."""
        source_path = Path(source)
        dest_path = Path(f"{dest}.gz")
        if not source_path.exists():
            return
        with source_path.open("rb") as source_file:
            with gzip.open(dest_path, "wb") as dest_file:
                shutil.copyfileobj(source_file, dest_file)
        source_path.unlink()


def configure_logging(log_dir: Path, level: str) -> None:
    """Configure console logging and 30-day compressed file retention."""
    ensure_directory(log_dir)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    file_handler = GZipTimedRotatingFileHandler(
        log_dir / "vast-revenue-monitor.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        utc=True,
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logging.basicConfig(
        level=numeric_level,
        handlers=[file_handler, console_handler],
        force=True,
    )
