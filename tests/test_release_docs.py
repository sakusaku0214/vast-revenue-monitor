from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_release_version_is_1_1_1():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "1.1.1"


def test_bilingual_readmes_link_and_document_operator_settings():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    japanese = (ROOT / "README.ja.md").read_text(encoding="utf-8")
    assert "English | [日本語](README.ja.md)" in english
    assert "[English](README.md) | 日本語" in japanese
    for document in (english, japanese):
        assert "reconfigure.sh" in document
        assert "weekly_goal_usd" in document
        assert "language" in document
        assert "v1.1.1" in document
