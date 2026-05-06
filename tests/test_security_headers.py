from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import install_security_middleware


def _make_client(max_body_bytes: int = 4096) -> TestClient:
    app = FastAPI()
    install_security_middleware(app, max_body_bytes=max_body_bytes)

    @app.get("/")
    def _root():
        return {"ok": True}

    @app.post("/x")
    async def _x():
        return {"ok": True}

    return TestClient(app)


def test_security_headers_present():
    client = _make_client()
    r = client.get("/")
    h = {k.lower(): v for k, v in r.headers.items()}
    assert "strict-transport-security" in h
    assert "content-security-policy" in h
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert "x-content-type-options" in h
    assert "permissions-policy" in h
    assert "referrer-policy" in h


def test_body_size_413_via_content_length():
    client = _make_client(max_body_bytes=10)
    r = client.post("/x", content=b"x" * 100)
    assert r.status_code == 413
