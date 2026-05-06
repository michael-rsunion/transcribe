import pytest
from pydantic import ValidationError


def test_loads_with_required_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_test_long_enough")
    monkeypatch.setenv("BASIC_AUTH_USER", "u")
    monkeypatch.setenv("BASIC_AUTH_PASS", "p" * 24)
    monkeypatch.setenv("HMAC_LOG_SECRET", "s" * 64)
    from app.config import Settings

    s = Settings()
    assert s.GEMINI_API_KEY == "AIza_test_long_enough"
    assert s.MAX_VIDEO_DURATION_SEC == 600
    assert s.GEMINI_MODEL == "gemini-2.5-flash"


def test_fails_without_required(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("BASIC_AUTH_PASS", raising=False)
    monkeypatch.delenv("HMAC_LOG_SECRET", raising=False)
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_password_min_length_enforced(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_long_enough")
    monkeypatch.setenv("BASIC_AUTH_USER", "u")
    monkeypatch.setenv("BASIC_AUTH_PASS", "short")
    monkeypatch.setenv("HMAC_LOG_SECRET", "s" * 64)
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_hmac_secret_min_length(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_long_enough")
    monkeypatch.setenv("BASIC_AUTH_USER", "u")
    monkeypatch.setenv("BASIC_AUTH_PASS", "x" * 24)
    monkeypatch.setenv("HMAC_LOG_SECRET", "tooshort")
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
