"""Release version loaded from the repository's single VERSION file."""
from pathlib import Path

VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text(
    encoding="utf-8"
).strip()


def footer_text() -> str:
    """Return the stable Discord product footer."""
    return f"Vast Revenue Monitor v{VERSION}"
