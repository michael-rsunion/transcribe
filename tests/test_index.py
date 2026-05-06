import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import reset_failed_auth_for_tests
from app.routes.index import router


@pytest.fixture(autouse=True)
def _reset_auth():
    reset_failed_auth_for_tests()
    yield
    reset_failed_auth_for_tests()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _basic(u: str, p: str) -> str:
    return "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()


def test_index_requires_auth(client):
    r = client.get("/")
    assert r.status_code == 401


def test_index_renders_with_auth(client):
    r = client.get("/", headers={"Authorization": _basic("equipo", "x" * 24)})
    assert r.status_code == 200
    assert "<form" in r.text
    assert "/transcribe" in r.text
