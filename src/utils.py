"""Utility helpers."""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


def ensure_directory(path: Path) -> None:
    """Create a directory and parents when missing."""
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default_factory: Callable[[], T]) -> T:
    """Read JSON, creating the file with a default value if missing."""
    if not path.exists():
        value = default_factory()
        write_json(path, value)
        return value
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"State file is invalid JSON and was preserved for recovery: {path}"
        ) from exc
    except OSError as exc:
        raise OSError(f"Unable to read state file {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    """Atomically write JSON to disk."""
    ensure_directory(path.parent)
    existing = path.stat() if path.exists() else None
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(data, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    temp_path = Path(temp_name)
    try:
        temp_path.chmod(existing.st_mode & 0o7777 if existing else 0o600)
        if existing:
            os.chown(temp_path, existing.st_uid, existing.st_gid)
        temp_path.replace(path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temp_path.unlink(missing_ok=True)


def utc_iso(value: datetime) -> str:
    """Serialize datetime as ISO-8601."""
    return value.isoformat()
