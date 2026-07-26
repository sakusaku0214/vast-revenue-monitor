"""Discord webhook embed rendering and delivery."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import __version__
from src.i18n import JA_PERIODS, RECORD_TITLES, normalize_language, translations
from src.models import Change, GoalStatus, Period, RecordBreak, ReportStatus, RevenueSnapshot

COLOR_BY_STATUS = {
    ReportStatus.NORMAL: 0x2ECC71,
    ReportStatus.ATTENTION: 0xF1C40F,
    ReportStatus.WARNING: 0xE74C3C,
    ReportStatus.RECORD: 0xD4AF37,
}
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscordNotifier:
    """Send rich Discord webhook notifications."""

    webhook_url: str
    timeout_seconds: int
    weekly_goal_usd: float = 1000.0
    detailed_report: bool = False
    timezone_name: str = "Asia/Tokyo"
    language: str = "en"

    @property
    def _text(self) -> dict[str, str]:
        return translations(self.language)

    def validate_webhook(self) -> None:
        """Verify webhook credentials without posting a Discord message."""
        session = requests.Session()
        try:
            retry = Retry(
                total=4,
                backoff_factor=1,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET",),
            )
            session.mount("https://", HTTPAdapter(max_retries=retry))
            response = session.get(self.webhook_url, timeout=self.timeout_seconds)
            try:
                response.raise_for_status()
                payload = response.json()
            finally:
                response.close()
        finally:
            session.close()
        name = payload.get("name") if isinstance(payload, dict) else None
        LOGGER.info("Discord webhook validation succeeded%s", f" ({name})" if name else "")

    def send_report(
        self,
        snapshot: RevenueSnapshot,
        usdjpy: float,
        changes: dict[str, Change],
        records: dict[Period, RecordBreak],
        goal: GoalStatus,
        highest: dict[Period, float] | None = None,
    ) -> None:
        """Send an hourly revenue report."""
        status = self._report_status(snapshot, {}, goal)
        self._post_embed(
            self._embed(snapshot, usdjpy, changes, {}, goal, status, highest)
        )
        for record in records.values():
            self._post_embed(self._record_embed(record))

    def send_schema_alert(self, message: str) -> None:
        """Notify Discord that the Vast.ai API schema could not be parsed."""
        self._post_embed({
            "title": self._text["schema_title"],
            "color": COLOR_BY_STATUS[ReportStatus.WARNING],
            "description": message,
            "fields": [{
                "name": self._text["action_required"],
                "value": self._text["schema_action"],
                "inline": False,
            }],
        })

    def _post_embed(self, embed: dict[str, Any]) -> None:
        session = requests.Session()
        try:
            retry = Retry(
                total=4,
                backoff_factor=1,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("POST",),
            )
            session.mount("https://", HTTPAdapter(max_retries=retry))
            response = session.post(
                self.webhook_url,
                json={"embeds": [embed]},
                timeout=self.timeout_seconds,
            )
            try:
                response.raise_for_status()
            finally:
                response.close()
        finally:
            session.close()

    def _embed(
        self,
        snapshot: RevenueSnapshot,
        usdjpy: float,
        changes: dict[str, Change],
        records: dict[Period, RecordBreak],
        goal: GoalStatus,
        status: ReportStatus,
        highest: dict[Period, float] | None = None,
    ) -> dict[str, Any]:
        fields = self._simple_revenue_fields(snapshot, usdjpy)
        fields.append(self._weekly_goal_field(snapshot.weekly_usd))
        fields.append(self._all_time_high_field(highest or {}))
        if self.detailed_report:
            fields.extend(self._performance_fields(snapshot, usdjpy, changes))
            fields.append(self._goal_field(goal))
        warning = self._gpu_warning_field(snapshot)
        if warning:
            fields.append(warning)
        local_time = snapshot.timestamp.astimezone(ZoneInfo(self.timezone_name))
        return {
            "title": self._text["title"],
            "color": COLOR_BY_STATUS[status],
            "fields": fields,
            "footer": {
                "text": (
                    f"Vast Revenue Monitor v{__version__} • USDJPY {usdjpy:.4f} • "
                    f"{local_time:%Y-%m-%d %H:%M JST}"
                )
            },
        }

    def _simple_revenue_fields(
        self,
        snapshot: RevenueSnapshot, rate: float
    ) -> list[dict[str, Any]]:
        text = self._text
        hourly_jpy = snapshot.hourly_usd * rate
        daily_jpy = snapshot.daily_usd * rate
        weekly_jpy = snapshot.weekly_usd * rate
        value = (
            f"{text['hourly']}  **${snapshot.hourly_usd:,.2f}** / ¥{hourly_jpy:,.0f}\n"
            f"{text['daily']}  **${snapshot.daily_usd:,.2f}** / ¥{daily_jpy:,.0f}\n"
            f"{text['weekly']}  **${snapshot.weekly_usd:,.2f}** / ¥{weekly_jpy:,.0f}"
        )
        return [{"name": text["revenue"], "value": value, "inline": False}]

    def _weekly_goal_field(self, current: float) -> dict[str, Any]:
        remaining = max(self.weekly_goal_usd - current, 0.0)
        progress = current / self.weekly_goal_usd * 100.0
        return {
            "name": self._text["weekly_goal"],
            "value": (
                f"{self._text['current']}: ${current:,.2f}\n"
                f"{self._text['goal']}: ${self.weekly_goal_usd:,.2f}\n"
                f"{self._text['progress']}: {progress:.1f}%\n"
                f"{self._text['remaining']}: ${remaining:,.2f}"
            ),
            "inline": True,
        }

    def _all_time_high_field(self, highest: dict[Period, float]) -> dict[str, Any]:
        return {
            "name": self._text["all_time_high"],
            "value": "\n".join(
                f"{self._text[period.value]}: ${highest.get(period, 0.0):,.2f}"
                for period in Period
            ),
            "inline": True,
        }

    def _record_embed(self, record: RecordBreak) -> dict[str, Any]:
        language = normalize_language(self.language)
        period = (
            JA_PERIODS[record.period.value]
            if language == "ja" else record.period.value.upper()
        )
        return {
            "title": RECORD_TITLES[language].format(period=period),
            "color": COLOR_BY_STATUS[ReportStatus.RECORD],
            "fields": [
                {
                    "name": self._text["current"],
                    "value": f"${record.current_usd:,.2f}",
                    "inline": True,
                },
                {
                    "name": self._text["previous"],
                    "value": f"${record.previous_best_usd:,.2f}",
                    "inline": True,
                },
                {
                    "name": self._text["improvement"],
                    "value": f"{record.improvement_percent:.1f}%",
                    "inline": True,
                },
            ],
        }

    def _performance_fields(
        self,
        snapshot: RevenueSnapshot,
        usdjpy: float,
        changes: dict[str, Change],
    ) -> list[dict[str, Any]]:
        return [
            self._period_field(
                self._text["hourly"], snapshot.hourly_usd, usdjpy, changes["hourly"]
            ),
            self._period_field(
                self._text["daily"], snapshot.daily_usd, usdjpy, changes["daily"]
            ),
            self._period_field(
                self._text["weekly"], snapshot.weekly_usd, usdjpy, changes["weekly"]
            ),
            self._period_field(
                self._text["monthly"], snapshot.monthly_usd, usdjpy, changes["monthly"]
            ),
        ]

    def _goal_field(self, goal: GoalStatus) -> dict[str, Any]:
        pace_label = (
            self._text["ahead"]
            if goal.pace_delta_percent >= 0
            else self._text["behind"]
        )
        return {
            "name": self._text["daily_goal"],
            "value": (
                f"{self._text['progress']}: ${goal.progress_usd:,.2f}\n"
                f"{self._text['remaining_daily']}: ${goal.remaining_usd:,.2f}\n"
                f"{self._text['current_progress']}: {goal.current_percent:.1f}%\n"
                f"{self._text['expected_progress']}: {goal.expected_percent:.1f}%\n"
                f"{pace_label}: {goal.pace_delta_percent:+.1f}%\n"
                f"{self._text['estimated_final']}: ${goal.estimated_final_usd:,.2f}\n"
                f"{self._text['status']}: "
                f"{self._text['on_track'] if goal.on_track else self._text['behind_pace']}"
            ),
            "inline": False,
        }

    def _gpu_warning_field(self, snapshot: RevenueSnapshot) -> dict[str, Any] | None:
        availability = snapshot.gpu_availability
        if availability is None or not availability.all_available:
            return None
        return {
            "name": self._text["gpu_warning"],
            "value": f"{availability.total} GPU(s) • {self._text['gpu_warning_body']}",
            "inline": False,
        }

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
    def _report_status(
        snapshot: RevenueSnapshot,
        records: dict[Period, RecordBreak],
        goal: GoalStatus,
    ) -> ReportStatus:
        if records:
            return ReportStatus.RECORD
        if snapshot.gpu_availability and snapshot.gpu_availability.all_available:
            return ReportStatus.WARNING
        if not goal.on_track:
            return ReportStatus.ATTENTION
        return ReportStatus.NORMAL
