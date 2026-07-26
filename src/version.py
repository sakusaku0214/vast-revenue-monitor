"""Release version sourced from the repository VERSION file."""
from pathlib import Path


VERSION = (
    (Path(__file__).resolve().parents[1] / "VERSION")
    .read_text(encoding="utf-8")
    .strip()
)
