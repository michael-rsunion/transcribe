import base64
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import reset_failed_auth_for_tests
from app.middleware import install_security_middleware
from app.routes.transcribe import router as t_router
from app.services.concurrency import reset_gate_for_tests


@pytest.fixture(autouse=True)
def _resets():
    reset_failed_auth_for_tests()
    reset_gate_for_tests()
    yield
    reset_failed_auth_for_tests()
    reset_gate_for_tests()


@pytest.fixture
def client():
    app = FastAPI()
    install_security_middleware(app, max_body_bytes=4096)
    app.include_router(t_router)
    return TestClient(app)


CREDS = {"Authorization": "Basic " + base64.b64encode(f"equipo:{'x'*24}".encode()).decode()}
JSON_CREDS = {**CREDS, "Accept": "application/json"}


def _setup_mocks(monkeypatch, tmp_path, *, duration=12.0, text="hola mundo"):
    def fake_download(_url, target_dir, **_kw):
        path = target_dir / "v.mp4"
        path.write_bytes(b"x")
        return path

    monkeypatch.setattr("app.routes.transcribe.download_video", fake_download)
    monkeypatch.setattr(
        "app.routes.transcribe.probe_duration_sec",
        AsyncMock(return_value=duration),
    )

    async def fake_extract(_src, target_dir, **_kw):
        out = target_dir / "a.mp3"
        out.write_bytes(b"x")
        return out

    monkeypatch.setattr("app.routes.transcribe.extract_audio_mp3", fake_extract)
    monkeypatch.setattr(
        "app.routes.transcribe.transcribe_audio",
        AsyncMock(return_value=text),
    )
    monkeypatch.setattr(
        "app.routes.transcribe.validate_url",
        lambda url: type("V", (), {"raw": url, "host": "x.com", "path": "/", "platform": "twitter"})(),
    )


def test_happy_path_json(client, tmp_path, monkeypatch):
    _setup_mocks(monkeypatch, tmp_path)
    r = client.post(
        "/transcribe",
        data={"url": "https://x.com/u/status/1"},
        headers=JSON_CREDS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["texto"] == "hola mundo"
    assert body["platform"] == "twitter"
    assert body["modelo"] == "gemini-2.5-flash"


def test_rejects_bad_url_returns_400(client, tmp_path, monkeypatch):
    from app.services.url_validator import UrlValidationError

    def bad(_url):
        raise UrlValidationError("nope")

    monkeypatch.setattr("app.routes.transcribe.validate_url", bad)
    r = client.post(
        "/transcribe",
        data={"url": "https://evil.com/"},
        headers=JSON_CREDS,
    )
    assert r.status_code == 400


def test_rejects_long_video_returns_413(client, tmp_path, monkeypatch):
    _setup_mocks(monkeypatch, tmp_path, duration=999.0)
    r = client.post(
        "/transcribe",
        data={"url": "https://x.com/u/status/1"},
        headers=JSON_CREDS,
    )
    assert r.status_code == 413


def test_html_response_when_html_accepted(client, tmp_path, monkeypatch):
    _setup_mocks(monkeypatch, tmp_path)
    r = client.post(
        "/transcribe",
        data={"url": "https://x.com/u/status/1"},
        headers={**CREDS, "Accept": "text/html"},
    )
    assert r.status_code == 200
    assert "hola mundo" in r.text
