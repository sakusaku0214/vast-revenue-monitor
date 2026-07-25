from __future__ import annotations

import pytest

from src.utils import read_json, write_json


def test_write_json_is_private_and_round_trips(tmp_path):
    path = tmp_path / "state" / "data.json"

    write_json(path, {"value": 1})

    assert path.stat().st_mode & 0o777 == 0o600
    assert read_json(path, dict) == {"value": 1}


def test_read_json_preserves_and_reports_corrupt_state(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(ValueError, match="preserved for recovery"):
        read_json(path, dict)

    assert path.read_text(encoding="utf-8") == "{broken"


def test_write_json_rejects_non_finite_values(tmp_path):
    with pytest.raises(ValueError):
        write_json(tmp_path / "state.json", {"value": float("nan")})

    assert not (tmp_path / "state.json").exists()
