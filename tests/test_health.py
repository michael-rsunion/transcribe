from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.health import router


def test_health_no_auth_required():
    app = FastAPI()
    app.include_router(router)
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
