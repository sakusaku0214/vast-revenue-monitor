from __future__ import annotations

import io
import tarfile

import pytest

from src.backup import safe_extract


def _archive(path, entries):
    with tarfile.open(path, "w:gz") as handle:
        for name, content, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(content)
            handle.addfile(info, io.BytesIO(content))


def test_safe_extract_accepts_config_and_state(tmp_path):
    archive = tmp_path / "backup.tar.gz"
    _archive(archive, [("config.json", b"{}", tarfile.REGTYPE),
                       ("state/history.json", b"[]", tarfile.REGTYPE)])

    safe_extract(archive, tmp_path / "restore")

    assert (tmp_path / "restore/state/history.json").read_text() == "[]"


@pytest.mark.parametrize(
    "name,kind",
    [("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE),
     ("state/link", tarfile.SYMTYPE), ("state/fifo", tarfile.FIFOTYPE),
     ("state/device", tarfile.CHRTYPE), ("logs/debug.log", tarfile.REGTYPE)],
)
def test_safe_extract_rejects_unsafe_entries(tmp_path, name, kind):
    archive = tmp_path / "bad.tar.gz"
    _archive(archive, [("config.json", b"{}", tarfile.REGTYPE), (name, b"", kind)])

    with pytest.raises(ValueError):
        safe_extract(archive, tmp_path / "restore")
