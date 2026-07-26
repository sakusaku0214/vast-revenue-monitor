from src.i18n import TRANSLATIONS, normalize_language


def test_all_languages_have_identical_keys():
    assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["ja"])


def test_unsupported_language_falls_back_to_english():
    assert normalize_language("xx") == "en"
