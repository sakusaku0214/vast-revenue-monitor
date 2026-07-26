"""Project version loaded from the canonical VERSION file."""
from pathlib import Path


def _load_version() -> str:
    version_path = Path(__file__).resolve().parent.parent / "VERSION"
    return version_path.read_text(encoding="utf-8").strip()


__version__ = _load_version()
