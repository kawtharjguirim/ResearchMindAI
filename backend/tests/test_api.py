import os
import time

os.environ["DATABASE_URL"] = "sqlite:///./test_researchmind.db"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-with-enough-length-for-hs256!"

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

SECRET = os.environ["SUPABASE_JWT_SECRET"]


def token(sub: str, **extra) -> str:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600, "email": f"{sub}@test.dev"}
    payload.update(extra)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def auth(sub: str) -> dict:
    return {"Authorization": f"Bearer {token(sub)}"}


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_is_public(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_me_requires_token(client):
    assert client.get("/api/v1/me").status_code == 401


def test_me_rejects_bad_signature(client):
    bad = jwt.encode({"sub": "x", "aud": "authenticated", "exp": int(time.time()) + 60}, "wrong" * 10, algorithm="HS256")
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_me_rejects_expired(client):
    expired = token("alice", exp=int(time.time()) - 10)
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_me_returns_user(client):
    r = client.get("/api/v1/me", headers=auth("alice"))
    assert r.status_code == 200
    assert r.json()["id"] == "alice"


def test_project_crud_and_isolation(client):
    body = {
        "title": "  Hybrid retrieval for scientific QA  ",
        "research_question": "Does a fine-tuned reranker beat BM25?",
        "objectives": ["Build baselines", "", "Fine-tune a reranker"],
        "hypotheses": ["H1"],
    }
    r = client.post("/api/v1/projects", json=body, headers=auth("alice"))
    assert r.status_code == 201
    p = r.json()
    assert p["title"] == "Hybrid retrieval for scientific QA"
    assert p["objectives"] == ["Build baselines", "Fine-tune a reranker"]
    assert p["status"] == "in_progress"

    assert len(client.get("/api/v1/projects", headers=auth("alice")).json()) == 1
    assert client.get("/api/v1/projects", headers=auth("bob")).json() == []
    assert client.get(f"/api/v1/projects/{p['id']}", headers=auth("bob")).status_code == 404
    assert client.delete(f"/api/v1/projects/{p['id']}", headers=auth("bob")).status_code == 404

    r = client.patch(f"/api/v1/projects/{p['id']}", json={"status": "writing", "progress": 80}, headers=auth("alice"))
    assert r.json()["status"] == "writing" and r.json()["progress"] == 80

    assert client.get("/api/v1/projects/stats", headers=auth("alice")).json()["active_projects"] == 1

    assert client.delete(f"/api/v1/projects/{p['id']}", headers=auth("alice")).status_code == 204
    assert client.get("/api/v1/projects", headers=auth("alice")).json() == []


def test_empty_title_rejected(client):
    r = client.post("/api/v1/projects", json={"title": "   "}, headers=auth("alice"))
    assert r.status_code == 422
