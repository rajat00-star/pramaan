"""Regression test for a real bug caught while writing .env.example: pydantic-
settings JSON-decodes env values for tuple/list-typed fields, which crashes on
a plain comma-separated string. cors_allow_origins is deliberately a `str` with
a parsed `.cors_allow_origins_list` property instead — this proves that stays true."""

from app.config import Settings


def test_cors_allow_origins_parses_comma_separated_env_value(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:8000,https://example.gov.in")
    settings = Settings(_env_file=None)
    assert settings.cors_allow_origins_list == ("http://localhost:8000", "https://example.gov.in")


def test_cors_allow_origins_default_is_not_wildcard():
    settings = Settings(_env_file=None)
    assert "*" not in settings.cors_allow_origins_list
    assert len(settings.cors_allow_origins_list) >= 1


def test_cors_allow_origins_handles_trailing_comma_and_whitespace(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", " http://a.example.com , http://b.example.com ,")
    settings = Settings(_env_file=None)
    assert settings.cors_allow_origins_list == ("http://a.example.com", "http://b.example.com")
