"""Discord webhook embed rendering and delivery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import Change, GoalStatus, Period, RevenueSnapshot

GOLD = 0xD4AF37
BLUE = 0x2F80ED


@dataclass(frozen=True)
class DiscordNotifier:
    """Send rich Discord webhook notifications."""

    webhook_url: str
    timeout_seconds: int

    def send_report(
        self,
        snapshot: RevenueSnapshot,
        usdjpy: float,
        changes: dict[str, Change],
        records: set[Period],
        goal: GoalStatus,
    ) -> None:
        """Send an hourly revenue report."""
        session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        response = session.post(
            self.webhook_url,
            json={"embeds": [self._embed(snapshot, usdjpy, changes, records, goal)]},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

    def _embed(
        self,
        snapshot: RevenueSnapshot,
        usdjpy: float,
        changes: dict[str, Change],
        records: set[Period],
        goal: GoalStatus,
    ) -> dict[str, Any]:
        title = "Vast.ai Revenue Report"
        if records:
            title = "🎉 NEW RECORD — Vast.ai Revenue Report"
        fields = [
            self._period_field(
                "Hourly", snapshot.hourly_usd, usdjpy,
                changes["hourly"], Period.HOURLY in records,
            ),
            self._period_field(
                "Daily", snapshot.daily_usd, usdjpy,
                changes["daily"], Period.DAILY in records,
            ),
            self._period_field(
                "Weekly", snapshot.weekly_usd, usdjpy,
                changes["weekly"], Period.WEEKLY in records,
            ),
            self._period_field(
                "Monthly", snapshot.monthly_usd, usdjpy,
                changes["monthly"], Period.MONTHLY in records,
            ),
            {
                "name": "Daily Goal",
                "value": (
                    f"Progress: ${goal.progress_usd:,.2f}\n"
                    f"Remaining: ${goal.remaining_usd:,.2f}\n"
                    f"Percent: {goal.percent:.1f}%\n"
                    f"Estimated final: ${goal.estimated_final_usd:,.2f}\n"
                    f"Status: {'On Track' if goal.on_track else 'Behind Pace'}"
                ),
                "inline": False,
            },
        ]
        return {
            "title": title,
            "color": GOLD if records else BLUE,
            "description": f"Performance at {snapshot.timestamp.isoformat()}",
            "fields": fields,
            "footer": {"text": f"USDJPY {usdjpy:.4f}"},
        }

    @staticmethod
    def _period_field(
        name: str,
        usd: float,
        rate: float,
        change: Change,
        record: bool,
    ) -> dict[str, Any]:
        arrow = "▲" if change.amount_usd >= 0 else "▼"
        record_text = "\n🎉 NEW RECORD" if record else ""
        return {
            "name": name,
            "value": (
                f"${usd:,.2f} / ¥{usd * rate:,.0f}\n"
                f"{arrow} ${abs(change.amount_usd):,.2f} ({abs(change.percent):.1f}%)"
                f"{record_text}"
            ),
            "inline": True,
        }
