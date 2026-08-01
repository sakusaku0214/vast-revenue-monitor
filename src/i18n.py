"""Centralized user-facing Discord translations."""
from __future__ import annotations

CATALOG = {
    "en": {
        "title": "💰 VAST.AI HOURLY REPORT", "revenue": "Revenue",
        "hourly": "Hourly", "daily": "Today", "yesterday": "Yesterday", "weekly": "Weekly", "monthly": "Monthly",
        "weekly_goal": "Weekly Goal", "current": "Current", "goal": "Goal",
        "progress": "Progress", "remaining_goal": "Remaining to Goal",
        "all_time_high": "All Time High", "previous": "Previous", "improvement": "Improvement",
        "record": "🏆 NEW {period} RECORD", "daily_goal": "Daily Goal",
        "remaining": "Remaining", "current_progress": "Current Progress",
        "expected_progress": "Expected Progress", "ahead": "Ahead", "behind": "Behind",
        "estimated_final": "Estimated final", "status": "Status", "on_track": "On Track",
        "behind_pace": "Behind Pace", "gpu_title": "⚠️ All GPUs Available",
        "gpu_text": "Detected {total} configured GPU(s) with no active rentals. Check pricing, host health, and Vast.ai listing status.",
        "schema_title": "⚠️ Vast.ai API Schema Alert", "action_required": "Action required",
        "schema_action": "Enable DEBUG logging and inspect `logs/api_response.json`.",
    },
    "ja": {
        "title": "💰 VAST.AI 毎時収益レポート", "revenue": "収益",
        "hourly": "直近区間", "daily": "本日", "yesterday": "昨日", "weekly": "今週", "monthly": "今月",
        "weekly_goal": "週間目標", "current": "現在", "goal": "目標",
        "progress": "進捗", "remaining_goal": "目標まで残り", "all_time_high": "過去最高",
        "previous": "前回", "improvement": "改善率", "record": "🏆 {period}収益の最高記録を更新",
        "daily_goal": "日間目標", "remaining": "残り", "current_progress": "現在の進捗",
        "expected_progress": "期待進捗", "ahead": "先行", "behind": "遅れ",
        "estimated_final": "最終予測", "status": "状態", "on_track": "順調",
        "behind_pace": "目標ペース未満", "gpu_title": "⚠️ すべてのGPUが利用可能",
        "gpu_text": "設定済みGPU {total}台に稼働中のレンタルがありません。価格、ホスト状態、Vast.ai掲載状態を確認してください。",
        "schema_title": "⚠️ Vast.ai APIスキーマ警告", "action_required": "必要な対応",
        "schema_action": "DEBUGログを有効にし、`logs/api_response.json`を確認してください。",
    },
}
PERIOD = {"en": {"hourly":"HOURLY","daily":"DAILY","weekly":"WEEKLY","monthly":"MONTHLY"},
          "ja": {"hourly":"時間","daily":"日間","weekly":"週間","monthly":"月間"}}

def translations(language: str) -> dict[str, str]:
    """Return a complete catalog, falling back to English."""
    return CATALOG.get(language, CATALOG["en"])
