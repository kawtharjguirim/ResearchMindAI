"""
Routes /papers : article arXiv du corpus (métadonnées, passage cité, PDF). Les fichiers
documents.jsonl / chunks.jsonl / PDF sont remplacés par un petit corpus dans tmp_path.
"""
import json
import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_researchmind.db")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-with-enough-length-for-hs256!")

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import arxiv_docs  # noqa: E402

API = "/api/v1"
PDF = b"%PDF-1.4 fake"


def auth(sub: str = "alice") -> dict:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {jwt.encode(payload, os.environ['SUPABASE_JWT_SECRET'], 'HS256')}"}


@pytest.fixture
def corpus(monkeypatch, tmp_path):
    data = tmp_path / "data"
    (data / "index").mkdir(parents=True)
    (data / "pdf" / "biologie").mkdir(parents=True)
    (data / "pdf" / "biologie" / "2204.13048.pdf").write_bytes(PDF)
    docs = [
        {"doc_id": "2204.13048", "domain": "biologie", "title": "TERMinator", "categories": "q-bio.BM",
         "license": "http://creativecommons.org/licenses/by/4.0/", "arxiv_url": "https://arxiv.org/abs/2204.13048",
         "pdf_path": "pdf/biologie/2204.13048.pdf", "abstract": "Protein design."},
        {"doc_id": "9999.0001", "domain": "maths", "title": "Sans PDF", "pdf_path": "pdf/maths/9999.0001.pdf"},
        {"doc_id": "6666.0001", "domain": "maths", "title": "Evasion", "pdf_path": "../../secret.pdf"},
    ]
    (data / "index" / "documents.jsonl").write_text("\n".join(json.dumps(d) for d in docs), encoding="utf-8")
    (tmp_path / "secret.pdf").write_bytes(b"secret")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text("\n".join(json.dumps(c) for c in [
        {"chunk_id": "2204.13048_0018", "document_id": "2204.13048", "source": "article",
         "section": "Model", "text": "Each residue gets an embedding."},
        {"chunk_id": "9999.0001_0000", "document_id": "9999.0001", "source": "article", "section": "", "text": "x"},
    ]), encoding="utf-8")

    monkeypatch.setattr(arxiv_docs, "DATA_DIR", data)
    monkeypatch.setattr(arxiv_docs, "DOCUMENTS", data / "index" / "documents.jsonl")
    monkeypatch.setattr(arxiv_docs, "CHUNKS", chunks)
    arxiv_docs._documents.cache_clear()
    arxiv_docs._chunks.cache_clear()
    yield
    arxiv_docs._documents.cache_clear()
    arxiv_docs._chunks.cache_clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_library_lists_all_papers_sorted_by_title(client, corpus):
    r = client.get(f"{API}/papers", headers=auth())
    assert r.status_code == 200
    papers = r.json()
    assert [p["title"] for p in papers] == ["Evasion", "Sans PDF", "TERMinator"]
    terminator = papers[2]
    assert terminator["has_pdf"] is True and terminator["domain"] == "biologie"
    assert {p["doc_id"]: p["has_pdf"] for p in papers}["9999.0001"] is False


def test_requires_token(client, corpus):
    assert client.get(f"{API}/papers").status_code == 401
    assert client.get(f"{API}/papers/2204.13048").status_code == 401
    assert client.get(f"{API}/papers/2204.13048/pdf").status_code == 401


def test_metadata_with_cited_passage(client, corpus):
    r = client.get(f"{API}/papers/2204.13048", params={"chunk": "2204.13048_0018"}, headers=auth())
    assert r.status_code == 200
    p = r.json()
    assert p["title"] == "TERMinator" and p["has_pdf"] is True
    assert p["passage"] == {"chunk_id": "2204.13048_0018", "section": "Model", "text": "Each residue gets an embedding."}


def test_passage_from_another_paper_is_ignored(client, corpus):
    r = client.get(f"{API}/papers/2204.13048", params={"chunk": "9999.0001_0000"}, headers=auth())
    assert r.status_code == 200 and r.json()["passage"] is None


def test_unknown_paper_is_404(client, corpus):
    assert client.get(f"{API}/papers/0000.0000", headers=auth()).status_code == 404
    assert client.get(f"{API}/papers/0000.0000/pdf", headers=auth()).status_code == 404


def test_pdf_is_served(client, corpus):
    r = client.get(f"{API}/papers/2204.13048/pdf", headers=auth())
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf" and r.content == PDF


def test_missing_pdf_is_404(client, corpus):
    assert client.get(f"{API}/papers/9999.0001", headers=auth()).json()["has_pdf"] is False
    assert client.get(f"{API}/papers/9999.0001/pdf", headers=auth()).status_code == 404


def test_pdf_path_outside_data_dir_is_refused(client, corpus):
    assert client.get(f"{API}/papers/6666.0001/pdf", headers=auth()).status_code == 404
