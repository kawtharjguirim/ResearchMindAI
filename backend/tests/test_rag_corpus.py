"""
Mode "corpus réel" de app.services.papers (pont vers rag/, voir app.services.rag_corpus).
rag/ n'est pas installé dans cet environnement de test : on force sa disponibilité par
monkeypatch pour vérifier le branchement, sans dépendre des modèles ni d'Ollama.
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
from app.services import papers, rag_corpus  # noqa: E402

API = "/api/v1"


def auth(sub: str) -> dict:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {jwt.encode(payload, os.environ['SUPABASE_JWT_SECRET'], 'HS256')}"}


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def real_corpus(monkeypatch):
    monkeypatch.setattr(rag_corpus, "disponible", lambda: True)
    monkeypatch.setattr(papers, "_nb_chunks_corpus", lambda: 3867)


def test_sources_list_shows_single_corpus_source_when_rag_is_available(client, real_corpus):
    r = client.get(f"{API}/sources", headers=auth("alice"))
    assert r.status_code == 200
    papers_sources = [s for s in r.json() if s["source_type"] != "video"]
    assert papers_sources == [{
        "id": "corpus-arxiv", "project_id": None, "source_type": "pdf",
        "title": "Corpus arXiv (data_latex)", "url": "", "language": "en", "duration": None,
        "status": "ready", "error": "",
        "excerpt": papers_sources[0]["excerpt"],
        "chunk_count": 3867, "created_at": papers_sources[0]["created_at"],
        "updated_at": papers_sources[0]["updated_at"],
    }]


def test_answer_on_corpus_delegates_to_rag_module(client, real_corpus, monkeypatch):
    def fake_answer(query, top_k=5):
        return {"reponse": "Les clients corrigent la dérive relativiste [1].",
                "citations": [{"chunk_id": "2204.13048_0007", "document_id": "2204.13048", "source": "article"}],
                "verifie": True}

    def fake_search(query, top_k=5):
        return [{"chunk_id": "2204.13048_0007", "document_id": "2204.13048", "source": "article",
                "text": "Les horloges satellites doivent corriger la dérive relativiste.", "score": 0.91}]

    monkeypatch.setattr(rag_corpus, "_rag", lambda: type("M", (), {"answer": staticmethod(fake_answer),
                                                                    "search": staticmethod(fake_search)}))
    r = client.post(f"{API}/answer", json={"source_id": "corpus-arxiv", "question": "Comment corriger la dérive ?"},
                    headers=auth("alice"))
    assert r.status_code == 200
    a = r.json()
    assert a["verifie"] is True
    assert a["citations"] == [{"chunk_id": "2204.13048_0007", "document_id": "2204.13048",
                               "source": "arXiv:2204.13048",
                               "text": "Les horloges satellites doivent corriger la dérive relativiste.",
                               "timestamp": None, "url": "/papers/2204.13048?chunk=2204.13048_0007"}]


def test_search_on_corpus_delegates_to_rag_module(client, real_corpus, monkeypatch):
    def fake_search(query, top_k=5):
        return [{"chunk_id": "c1", "document_id": "9999.0001", "source": "article", "text": "texte", "score": 0.5}]

    monkeypatch.setattr(rag_corpus, "_rag", lambda: type("M", (), {"search": staticmethod(fake_search)}))
    r = client.post(f"{API}/search", json={"query": "texte", "source_id": "corpus-arxiv"}, headers=auth("alice"))
    assert r.status_code == 200
    assert r.json() == [{"chunk_id": "c1", "document_id": "9999.0001", "source": "arXiv:9999.0001",
                         "text": "texte", "score": 0.5, "timestamp": None}]


def test_answer_when_rag_missing_dependencies_is_503(client, real_corpus, monkeypatch):
    monkeypatch.setattr(rag_corpus, "dependances_manquantes", lambda: ["rank_bm25"])
    r = client.post(f"{API}/answer", json={"source_id": "corpus-arxiv", "question": "?"}, headers=auth("alice"))
    assert r.status_code == 503 and "rank_bm25" in r.json()["detail"]
