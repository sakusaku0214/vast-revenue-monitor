from pathlib import Path


def test_release_and_bilingual_documentation_are_consistent():
    assert Path("VERSION").read_text().strip() == "1.0.0"
    english = Path("README.md").read_text()
    japanese = Path("README.ja.md").read_text()
    assert "[日本語](README.ja.md)" in english
    assert "[English](README.md)" in japanese
    for document in (english, japanese):
        assert "v1.0.0" in document
        assert "reconfigure.sh" in document
        assert "weekly_goal_usd" in document
        assert "language" in document
