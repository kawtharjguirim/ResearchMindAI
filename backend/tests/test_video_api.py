"""
Routes /sources/video et /ask. Les modèles (Whisper, E5, reranker) et Ollama sont remplacés
par des doublures : on teste l'API, l'isolation entre utilisateurs et le pipeline extractif.
"""
import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_researchmind.db")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-with-enough-length-for-hs256!")

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.video import llm, pipeline  # noqa: E402

API = "/api/v1"
SEGMENTS = [
    {"start": 0.0, "end": 4.0, "text": "Le GPS doit corriger l'effet de la relativité."},
    {"start": 4.0, "end": 9.0, "text": "Sans cette correction, la position dériverait"},
    {"start": 9.0, "end": 12.0, "text": "de dix kilomètres par jour."},
    {"start": 60.0, "end": 70.0, "text": "Passons maintenant à la cuisine italienne."},
]


def auth(sub: str) -> dict:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {jwt.encode(payload, os.environ['SUPABASE_JWT_SECRET'], 'HS256')}"}


class FakeIndex:
    """Doublure de search.Index : scores de reranking fixés par le test."""
    rerank = 0.9

    def __init__(self, chunks, embeddings=None):
        assert embeddings is not None and len(embeddings) == len(chunks)
        self.chunks = chunks

    def rechercher(self, question):
        return [{"chunk": c, "rerank": self.rerank / (k + 1)} for k, c in enumerate(self.chunks)]

    def scorer(self, question, textes):
        return [0.5] * len(textes)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def fake_models(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "VIDEOS_DIR", tmp_path)
    monkeypatch.setattr("app.api.routes.sources.VIDEOS_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "dependances_manquantes", lambda: [])
    monkeypatch.setattr(pipeline, "transcrire", lambda chemin, langue: {
        "source": os.path.basename(chemin), "language": "fr", "duration": 70.0, "segments": SEGMENTS})
    monkeypatch.setattr(pipeline, "encoder_passages", lambda textes: [[0.1, 0.2] for _ in textes])
    monkeypatch.setattr(pipeline, "Index", FakeIndex)
    pipeline._cache.clear()
    return tmp_path


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def upload(client, user="alice", filename="cours.mp4", body=b"fake video bytes", **params):
    return client.post(f"{API}/sources/video", params={"filename": filename, **params},
                       content=body, headers={**auth(user), "Content-Type": "video/mp4"})


def test_upload_requires_token(client):
    assert client.post(f"{API}/sources/video", params={"filename": "a.mp4"}, content=b"x").status_code == 401


def test_upload_without_video_group_returns_503(client, monkeypatch):
    monkeypatch.setattr(pipeline, "dependances_manquantes", lambda: ["faster_whisper"])
    r = upload(client)
    assert r.status_code == 503 and "uv sync --group video" in r.json()["detail"]


def test_upload_rejects_bad_format_and_empty_body(client, fake_models):
    assert upload(client, filename="notes.pdf").status_code == 415
    assert upload(client, body=b"").status_code == 400
    assert list(fake_models.iterdir()) == []          # aucun fichier laissé sur le disque


def test_upload_processes_video_and_isolates_users(client, fake_models):
    r = upload(client, title="  Relativité et GPS  ")
    assert r.status_code == 202
    s = r.json()
    assert s["status"] == "pending" and s["title"] == "Relativité et GPS"
    assert len(list(fake_models.iterdir())) == 1      # vidéo stockée

    # La tâche de fond a tourné : la source est prête, avec ses chunks
    s = client.get(f"{API}/sources/{s['id']}", headers=auth("alice")).json()
    assert s["status"] == "ready" and s["chunk_count"] >= 1 and s["duration"] == 70.0

    def video_ids(user):
        return [x["id"] for x in client.get(f"{API}/sources", headers=auth(user)).json() if x["source_type"] == "video"]

    assert video_ids("alice") == [s["id"]]
    assert video_ids("bob") == []
    assert client.get(f"{API}/sources/{s['id']}", headers=auth("bob")).status_code == 404
    assert client.delete(f"{API}/sources/{s['id']}", headers=auth("bob")).status_code == 404

    assert client.delete(f"{API}/sources/{s['id']}", headers=auth("alice")).status_code == 204
    assert video_ids("alice") == []
    assert list(fake_models.iterdir()) == []          # vidéo supprimée du disque


def test_processing_error_is_stored(client, fake_models, monkeypatch):
    def boom(chemin, langue):
        raise RuntimeError("CUDA introuvable")
    monkeypatch.setattr(pipeline, "transcrire", boom)
    s = upload(client).json()
    s = client.get(f"{API}/sources/{s['id']}", headers=auth("alice")).json()
    assert s["status"] == "error" and "CUDA introuvable" in s["error"]


def test_upload_to_someone_elses_project_is_refused(client, fake_models):
    p = client.post(f"{API}/projects", json={"title": "Projet de Bob"}, headers=auth("bob")).json()
    assert upload(client, project_id=p["id"]).status_code == 404


def test_answer_returns_exact_citation_with_timestamp(client, fake_models, monkeypatch):
    def fake_chat(messages, schema=None, appels=None, etape=None):
        if etape == "verification":
            return {"information_demandee": "conséquence", "extrait": 1, "repond": True,
                    "phrase": "Sans cette correction la position dériverait de dix kilomètres par jour"}
        return {"reformulation": "La position dériverait de dix kilomètres chaque jour sans correction."}
    monkeypatch.setattr(llm, "chat", fake_chat)

    s = upload(client).json()
    r = client.post(f"{API}/answer", json={"source_id": s["id"], "question": "Que se passe-t-il sans correction ?"},
                    headers=auth("alice"))
    assert r.status_code == 200
    a = r.json()
    assert a["status"] == "repondu" and a["verifie"] is True
    assert a["citations"] == [{
        "chunk_id": a["passages"][0]["chunk_id"], "document_id": s["id"], "source": s["title"],
        "text": "Sans cette correction, la position dériverait de dix kilomètres par jour.",
        "timestamp": "00:00:04", "url": None,
    }]
    assert a["reponse"].startswith("« Sans cette correction")
    assert len(a["passages"]) >= 1 and "recherche" in a["timings"]

    # Isolation : bob ne peut pas interroger la vidéo d'alice
    assert client.post(f"{API}/answer", json={"source_id": s["id"], "question": "?"},
                       headers=auth("bob")).status_code == 404


def test_answer_below_floor_is_off_topic_without_calling_llm(client, fake_models, monkeypatch):
    def no_llm(*a, **k):
        raise AssertionError("le LLM ne doit pas être appelé sous le plancher")
    monkeypatch.setattr(llm, "chat", no_llm)
    monkeypatch.setattr(FakeIndex, "rerank", 0.0147)
    s = upload(client).json()
    a = client.post(f"{API}/answer", json={"source_id": s["id"], "question": "Recette des lasagnes ?"},
                    headers=auth("alice")).json()
    assert a["status"] == "hors_sujet" and a["verifie"] is False and a["citations"] == []


def test_answer_on_unready_source_is_409(client, fake_models, monkeypatch):
    monkeypatch.setattr(pipeline, "traiter_source", lambda source_id: None)   # reste « pending »
    s = upload(client).json()
    r = client.post(f"{API}/answer", json={"source_id": s["id"], "question": "?"}, headers=auth("alice"))
    assert r.status_code == 409


def test_answer_when_ollama_is_down_is_503(client, fake_models, monkeypatch):
    def down(*a, **k):
        raise llm.OllamaIndisponible("Ollama injoignable")
    monkeypatch.setattr(llm, "chat", down)
    s = upload(client).json()
    r = client.post(f"{API}/answer", json={"source_id": s["id"], "question": "Et le GPS ?"}, headers=auth("alice"))
    assert r.status_code == 503 and "Ollama" in r.json()["detail"]


def test_empty_question_rejected(client, fake_models):
    s = upload(client).json()
    r = client.post(f"{API}/answer", json={"source_id": s["id"], "question": "   "}, headers=auth("alice"))
    assert r.status_code == 422


def test_answer_on_simulated_paper_source_is_marked_unverified(client):
    r = client.post(f"{API}/answer", json={"source_id": "paper-demo-rag", "question": "What is RAG?"},
                    headers=auth("alice"))
    assert r.status_code == 200
    a = r.json()
    assert a["verifie"] is False and len(a["citations"]) == 1


def test_sources_list_includes_simulated_papers(client):
    r = client.get(f"{API}/sources", headers=auth("alice"))
    assert r.status_code == 200
    types = {s["source_type"] for s in r.json()}
    assert "pdf" in types and "web" in types and "personal" in types


def test_search_returns_results_for_paper_source(client):
    r = client.post(f"{API}/search", json={"query": "relativistic GPS clocks", "source_id": "paper-demo-relativity"},
                    headers=auth("alice"))
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1 and results[0]["document_id"] == "paper-demo-relativity"


def test_search_across_all_sources_includes_video_and_papers(client, fake_models, monkeypatch):
    monkeypatch.setattr(FakeIndex, "rerank", 0.5)
    upload(client)
    r = client.post(f"{API}/search", json={"query": "GPS relativity", "top_k": 20}, headers=auth("alice"))
    assert r.status_code == 200
    doc_ids = {x["document_id"] for x in r.json()}
    assert "paper-demo-relativity" in doc_ids


def test_transcript_returns_chunks_in_order(client, fake_models):
    s = upload(client).json()
    r = client.get(f"{API}/sources/{s['id']}/transcript", headers=auth("alice"))
    assert r.status_code == 200
    chunks = r.json()
    assert len(chunks) >= 1
    assert chunks == sorted(chunks, key=lambda c: c["start"])
    assert client.get(f"{API}/sources/{s['id']}/transcript", headers=auth("bob")).status_code == 404


def test_play_link_then_file_streams_video(client, fake_models):
    s = upload(client).json()
    link = client.get(f"{API}/sources/{s['id']}/play-link", headers=auth("alice"))
    assert link.status_code == 200
    url = link.json()["url"]
    r = client.get(url)
    assert r.status_code == 200 and r.content == b"fake video bytes"
    # Jeton valide, mais pour une autre source dans l'URL : refusé.
    bad = client.get(url.replace(s["id"], "00000000-0000-0000-0000-000000000000"))
    assert bad.status_code in (401, 403, 404)
