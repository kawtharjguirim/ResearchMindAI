"""
Documents personnels (Word, Markdown, texte) : POST /sources/file. Les embeddings sont simulés.
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
from app.services import personnels  # noqa: E402
from app.services.video import pipeline  # noqa: E402

API = "/api/v1"
TEXTE = ("Ce document explique la relativité restreinte et la dilatation des durées. " * 12).encode("utf-8")


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
    return TestClient(app)


@pytest.fixture
def fake_docs(monkeypatch, tmp_path):
    monkeypatch.setattr(personnels, "DOCUMENTS_DIR", tmp_path, raising=False)
    monkeypatch.setattr("app.api.routes.sources.DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "encoder_passages", lambda textes: [[0.1] * 8 for _ in textes])
    return tmp_path


def docx_bytes(tmp_path) -> bytes:
    from docx import Document
    doc = Document()
    doc.add_heading("Notes de cours", level=1)
    doc.add_paragraph("La relativité restreinte relie l'espace et le temps à la vitesse de l'observateur.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Terme"
    table.rows[0].cells[1].text = "Définition"
    chemin = tmp_path / "source.docx"
    doc.save(str(chemin))
    return chemin.read_bytes()


# ---------- Lecture ----------

def test_texte_brut_et_markdown_sont_lus(tmp_path):
    chemin = tmp_path / "notes.md"
    chemin.write_bytes(b"# Titre\n\nUn paragraphe de test.")
    assert "Un paragraphe de test." in personnels.lire_texte_personnel(chemin)


def test_docx_lit_paragraphes_et_tableaux(tmp_path):
    chemin = tmp_path / "cours.docx"
    chemin.write_bytes(docx_bytes(tmp_path))
    texte = personnels.lire_texte_personnel(chemin)
    assert "relativité restreinte" in texte
    assert "Terme | Définition" in texte


# ---------- Route POST /sources/file ----------

def test_texte_est_indexe(client, fake_docs):
    r = client.post(f"{API}/sources/file?filename=notes.txt", content=TEXTE,
                    headers={**auth("u1"), "Content-Type": "text/plain"})
    assert r.status_code == 202
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "ready"
    assert detail["source_type"] == "personal"
    assert detail["chunk_count"] >= 1


def test_docx_est_indexe(client, fake_docs):
    contenu = docx_bytes(fake_docs)
    r = client.post(f"{API}/sources/file?filename=cours.docx", content=contenu, headers=auth("u1"))
    assert r.status_code == 202
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "ready"
    assert detail["source_type"] == "personal"


def test_fichier_binaire_renomme_en_txt_est_refuse(client, fake_docs):
    r = client.post(f"{API}/sources/file?filename=faux.txt", content=b"\x00\x01binaire", headers=auth("u1"))
    assert r.status_code == 415


def test_docx_invalide_est_refuse(client, fake_docs):
    r = client.post(f"{API}/sources/file?filename=faux.docx", content=TEXTE, headers=auth("u1"))
    assert r.status_code == 415


def test_format_non_accepte(client, fake_docs):
    r = client.post(f"{API}/sources/file?filename=classeur.xlsx", content=TEXTE, headers=auth("u1"))
    assert r.status_code == 415
    assert "DOCX, MD, TXT" in r.json()["detail"]
