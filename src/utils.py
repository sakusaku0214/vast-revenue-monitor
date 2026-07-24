"""Utility helpers."""
from __future__ import annotations

import json
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
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    """Atomically write JSON to disk."""
    ensure_directory(path.parent)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_name = handle.name
    Path(temp_name).replace(path)


def utc_iso(value: datetime) -> str:
    """Serialize datetime as ISO-8601."""
    return value.isoformat()
