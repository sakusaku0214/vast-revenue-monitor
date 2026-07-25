from __future__ import annotations

import pytest

from src.scheduler import RevenueMonitor


def test_api_failure_does_not_update_revenue_state():
    class FailingApi:
        def get_account_balance(self):
            raise ConnectionError("Vast.ai unavailable")

    class RevenueSpy:
        called = False

        def update(self, _sample):
            self.called = True
            raise AssertionError("state must not be updated")

    monitor = RevenueMonitor.__new__(RevenueMonitor)
    monitor._vast = FailingApi()
    monitor._revenue = RevenueSpy()

    with pytest.raises(ConnectionError, match="unavailable"):
        monitor._fetch_snapshot_with_alert()

    assert monitor._revenue.called is False
