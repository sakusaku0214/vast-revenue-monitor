"""Safe validation and extraction for Vast Revenue Monitor backups."""
from __future__ import annotations

import argparse
import tarfile
from pathlib import Path, PurePosixPath

MAX_FILES = 10_000
MAX_TOTAL_BYTES = 1_073_741_824
ALLOWED_ROOTS = {"config.json", "state"}


def safe_extract(archive: Path, destination: Path) -> None:
    """Validate and extract an application backup into an empty directory."""
    total_size = 0
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        if len(members) > MAX_FILES:
            raise ValueError(f"Backup exceeds {MAX_FILES} entries")
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe backup path: {member.name}")
            if not path.parts or path.parts[0] not in ALLOWED_ROOTS:
                raise ValueError(f"Unexpected backup path: {member.name}")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsupported backup entry: {member.name}")
            total_size += member.size
            if total_size > MAX_TOTAL_BYTES:
                raise ValueError("Backup uncompressed size exceeds 1 GiB")
        if not any(member.name == "config.json" for member in members):
            raise ValueError("Backup has no config.json")
        destination.mkdir(parents=True, exist_ok=True)
        handle.extractall(destination, filter="data")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    safe_extract(args.archive, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
