import base64

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import require_basic_auth, reset_failed_auth_for_tests


def _basic(u: str, p: str) -> str:
    return "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()


@pytest.fixture(autouse=True)
def _reset():
    reset_failed_auth_for_tests()
    yield
    reset_failed_auth_for_tests()


@pytest.fixture
def client():
    app = FastAPI()

    @app.get("/secret")
    def secret(_: None = Depends(require_basic_auth)):
        return {"ok": True}

    return TestClient(app)


def test_no_auth_returns_401(client):
    r = client.get("/secret")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_correct_credentials_pass(client):
    r = client.get("/secret", headers={"Authorization": _basic("equipo", "x" * 24)})
    assert r.status_code == 200


def test_wrong_password_returns_401(client):
    r = client.get("/secret", headers={"Authorization": _basic("equipo", "wrong")})
    assert r.status_code == 401


def test_failed_auth_bucket_locks_after_threshold(client):
    # 5 failed attempts allowed, 6th gets locked (429)
    for _ in range(5):
        r = client.get(
            "/secret", headers={"Authorization": _basic("equipo", "wrong")}
        )
        assert r.status_code == 401
    r = client.get("/secret", headers={"Authorization": _basic("equipo", "wrong")})
    assert r.status_code == 429
