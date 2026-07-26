from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models import RevenueSnapshot


@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf")])
def test_snapshot_rejects_invalid_revenue(invalid):
    with pytest.raises(ValueError, match="finite and non-negative"):
        RevenueSnapshot(
            datetime.now(timezone.utc),
            invalid,
            1.0,
            1.0,
            1.0,
        )


def test_snapshot_requires_aware_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        RevenueSnapshot(datetime.now(), 1.0, 1.0, 1.0, 1.0)
