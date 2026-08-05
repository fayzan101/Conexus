from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.health import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
