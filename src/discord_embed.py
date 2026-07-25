"""Discord webhook embed rendering and delivery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import Change, GoalStatus, Period, RecordBreak, RevenueSnapshot

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
        records: dict[Period, RecordBreak],
        goal: GoalStatus,
    ) -> None:
        """Send an hourly revenue report."""
        session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("POST",),
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
        records: dict[Period, RecordBreak],
        goal: GoalStatus,
    ) -> dict[str, Any]:
        fields = self._performance_fields(snapshot, usdjpy, changes)
        fields.append(self._goal_field(goal))
        fields.extend(self._record_fields(records))
        return {
            "title": self._title(records),
            "color": GOLD if records else BLUE,
            "description": f"Performance at {snapshot.timestamp.isoformat()}",
            "fields": fields,
            "footer": {"text": f"USDJPY {usdjpy:.4f}"},
        }

    def _performance_fields(
        self,
        snapshot: RevenueSnapshot,
        usdjpy: float,
        changes: dict[str, Change],
    ) -> list[dict[str, Any]]:
        return [
            self._period_field("Hourly", snapshot.hourly_usd, usdjpy, changes["hourly"]),
            self._period_field("Daily", snapshot.daily_usd, usdjpy, changes["daily"]),
            self._period_field("Weekly", snapshot.weekly_usd, usdjpy, changes["weekly"]),
            self._period_field("Monthly", snapshot.monthly_usd, usdjpy, changes["monthly"]),
        ]

    @staticmethod
    def _goal_field(goal: GoalStatus) -> dict[str, Any]:
        pace_label = "Ahead" if goal.pace_delta_percent >= 0 else "Behind"
        return {
            "name": "Daily Goal",
            "value": (
                f"Progress: ${goal.progress_usd:,.2f}\n"
                f"Remaining: ${goal.remaining_usd:,.2f}\n"
                f"Current Progress: {goal.current_percent:.1f}%\n"
                f"Expected Progress: {goal.expected_percent:.1f}%\n"
                f"{pace_label}: {goal.pace_delta_percent:+.1f}%\n"
                f"Estimated final: ${goal.estimated_final_usd:,.2f}\n"
                f"Status: {'On Track' if goal.on_track else 'Behind Pace'}"
            ),
            "inline": False,
        }

    @staticmethod
    def _record_fields(records: dict[Period, RecordBreak]) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for period, record in records.items():
            fields.append({
                "name": f"🏆 NEW {period.value.upper()} RECORD",
                "value": (
                    f"Current: ${record.current_usd:,.2f}\n"
                    f"Previous best: ${record.previous_best_usd:,.2f}\n"
                    f"Improvement: {record.improvement_percent:.1f}%"
                ),
                "inline": False,
            })
        return fields

    @staticmethod
    def _period_field(
        name: str,
        usd: float,
        rate: float,
        change: Change,
    ) -> dict[str, Any]:
        arrow = "▲" if change.amount_usd >= 0 else "▼"
        return {
            "name": name,
            "value": (
                f"${usd:,.2f} / ¥{usd * rate:,.0f}\n"
                f"{arrow} ${abs(change.amount_usd):,.2f} ({abs(change.percent):.1f}%)"
            ),
            "inline": True,
        }

    @staticmethod
    def _title(records: dict[Period, RecordBreak]) -> str:
        if records:
            return "🎉 NEW RECORD — Vast.ai Revenue Report"
        return "Vast.ai Revenue Report"
