import json

import pytest

from src.reconfigure import parse_goal, reconfigure, select_language


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "text"])
def test_invalid_goals_are_rejected(value):
    with pytest.raises(ValueError):
        parse_goal(value, 1000)


def test_empty_values_preserve_current_settings():
    assert parse_goal("", 1200) == 1200
    assert select_language("", "ja") == "ja"


def test_reconfigure_preserves_secrets_and_unrelated_values(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"weekly_goal_usd": 1000, "language": "en",
                                "vast_api_key": "secret", "discord_webhook_url": "hidden",
                                "future_key": 42}))
    answers = iter(["1200.5", "2", "y"])

    output = []
    assert reconfigure(path, lambda _prompt: next(answers), output.append)
    result = json.loads(path.read_text())

    assert result["weekly_goal_usd"] == 1200.5
    assert result["language"] == "ja"
    assert result["vast_api_key"] == "secret"
    assert result["discord_webhook_url"] == "hidden"
    assert result["future_key"] == 42
    assert "secret" not in "\n".join(output)
    assert "hidden" not in "\n".join(output)
