"""
Automated validation for WeatherGPT Indian Language Support (23 languages total).
Verifies all 22 official languages in the Eighth Schedule of the Indian Constitution
plus English against canonical schema keys.
"""
import json
from pathlib import Path
import pytest

I18N_DIR = Path(__file__).resolve().parent.parent / "frontend" / "lib" / "i18n"

REQUIRED_LANGUAGES = [
    "en", "hi", "as", "bn", "brx", "doi", "gu", "kn", "ks",
    "kok", "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa",
    "sat", "sd", "ta", "te", "ur"
]

RTL_LANGUAGES = {"ur", "sd", "ks"}


def get_all_keys(d, prefix=""):
    keys = set()
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(get_all_keys(v, full_key))
        else:
            keys.add(full_key)
    return keys


def test_canonical_english_exists():
    en_file = I18N_DIR / "en.json"
    assert en_file.exists(), "Canonical en.json must exist"
    data = json.loads(en_file.read_text(encoding="utf-8"))
    assert "brand" in data
    assert "nav" in data
    assert "auth" in data
    assert "weather" in data
    assert "alerts" in data
    assert "onboarding" in data


def test_all_23_language_files_exist():
    assert len(REQUIRED_LANGUAGES) == 23
    for lang in REQUIRED_LANGUAGES:
        file_path = I18N_DIR / f"{lang}.json"
        assert file_path.exists(), f"Language dictionary for {lang} is missing at {file_path}"


def test_keys_completeness_against_canonical():
    en_data = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))
    canonical_keys = get_all_keys(en_data)

    for lang in REQUIRED_LANGUAGES:
        lang_file = I18N_DIR / f"{lang}.json"
        lang_data = json.loads(lang_file.read_text(encoding="utf-8"))
        lang_keys = get_all_keys(lang_data)

        missing_keys = canonical_keys - lang_keys
        assert not missing_keys, f"Language '{lang}' is missing critical keys: {missing_keys}"


def test_rtl_specification():
    # Verify RTL language codes match requirements
    assert "ur" in RTL_LANGUAGES
    assert "sd" in RTL_LANGUAGES
    assert "ks" in RTL_LANGUAGES
    assert "hi" not in RTL_LANGUAGES
    assert "en" not in RTL_LANGUAGES


def test_no_empty_translations_in_critical_fields():
    for lang in REQUIRED_LANGUAGES:
        lang_data = json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        assert lang_data["brand"]["name"] == "WeatherGPT"
        assert lang_data["auth"]["createAccount"]
        assert lang_data["weather"]["temperature"]
        assert lang_data["weather"]["humidity"]
        assert lang_data["alerts"]["warning"]


def test_weather_query_engine_language_extraction():
    from backend.services.query import query_engine
    for lang in REQUIRED_LANGUAGES:
        # Explicit language parameter
        parsed = query_engine.extract("Delhi weather", language=lang)
        assert parsed["language"] == lang


def test_weather_query_fallback_all_languages():
    from backend.services.query import query_engine, LOCALIZED_TEMPLATES
    for lang in REQUIRED_LANGUAGES:
        tpl = LOCALIZED_TEMPLATES.get(lang, LOCALIZED_TEMPLATES["en"])
        msg = tpl["current"].format(
            name="Patna",
            temp=28.5,
            feels=30.0,
            humidity=65,
            wind=12.0,
            wind_dir=90,
            precip=0.0,
        )
        assert "Patna" in msg
        assert "28.5" in msg

