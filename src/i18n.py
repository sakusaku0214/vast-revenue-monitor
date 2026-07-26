"""Centralized Discord notification translations."""
from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)
SUPPORTED_LANGUAGES = ("en", "ja")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "title": "💰 VAST.AI HOURLY REPORT", "revenue": "Revenue",
        "hourly": "Hourly", "daily": "Daily", "weekly": "Weekly",
        "monthly": "Monthly", "weekly_goal": "Weekly Goal",
        "current": "Current", "goal": "Goal", "progress": "Progress",
        "remaining": "Remaining to Goal", "all_time_high": "All Time High",
        "previous": "Previous", "improvement": "Improvement",
        "daily_goal": "Daily Goal", "remaining_daily": "Remaining",
        "estimated_final": "Estimated final", "status": "Status",
        "on_track": "On Track", "behind_pace": "Behind Pace",
        "current_progress": "Current Progress", "expected_progress": "Expected Progress",
        "ahead": "Ahead", "behind": "Behind",
        "gpu_warning": "⚠️ All GPUs Available",
        "gpu_warning_body": (
            "No active rentals detected. Check pricing, host health, and listing status."
        ),
        "schema_title": "⚠️ Vast.ai API Schema Alert",
        "action_required": "Action required",
        "schema_action": "Inspect the private API diagnostic response and service logs.",
    },
    "ja": {
        "title": "💰 VAST.AI 毎時収益レポート", "revenue": "収益",
        "hourly": "直近区間", "daily": "本日", "weekly": "今週",
        "monthly": "月間", "weekly_goal": "週間目標",
        "current": "現在", "goal": "目標", "progress": "進捗",
        "remaining": "目標まで残り", "all_time_high": "過去最高",
        "previous": "前回", "improvement": "伸び率",
        "daily_goal": "日間目標", "remaining_daily": "残り",
        "estimated_final": "最終予測", "status": "状況",
        "on_track": "順調", "behind_pace": "遅れ",
        "current_progress": "現在の進捗", "expected_progress": "期待進捗",
        "ahead": "先行", "behind": "遅れ",
        "gpu_warning": "⚠️ 全GPUが空いています",
        "gpu_warning_body": "稼働中のレンタルがありません。価格、ホスト状態、掲載状態を確認してください。",
        "schema_title": "⚠️ Vast.ai APIスキーマエラー",
        "action_required": "確認が必要です",
        "schema_action": "非公開のAPI診断レスポンスとサービスログを確認してください。",
    },
}

RECORD_TITLES = {
    "en": "🏆 NEW {period} RECORD",
    "ja": "🏆 {period}収益の最高記録を更新",
}
JA_PERIODS = {"hourly": "直近区間", "daily": "日間", "weekly": "週間", "monthly": "月間"}


def normalize_language(value: object) -> str:
    """Return a supported language, warning and falling back to English."""
    if value in SUPPORTED_LANGUAGES:
        return str(value)
    LOGGER.warning("Unsupported notification language %r; falling back to English", value)
    return "en"


def translations(language: str) -> dict[str, str]:
    """Return a complete translation mapping or fail loudly for missing keys."""
    return TRANSLATIONS[normalize_language(language)]
