"""Fixtures globales: env vars minimas para que Settings cargue en tests."""

import pytest


@pytest.fixture(autouse=True)
def _set_min_env(monkeypatch, tmp_path_factory):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_test_dummy_key_long_enough")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("BASIC_AUTH_USER", "equipo")
    monkeypatch.setenv("BASIC_AUTH_PASS", "x" * 24)
    monkeypatch.setenv("HMAC_LOG_SECRET", "s" * 64)
    base = tmp_path_factory.mktemp("transcribe-tmpfs")
    monkeypatch.setenv("TMPFS_BASE_DIR", str(base))
