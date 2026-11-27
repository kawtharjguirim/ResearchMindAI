"""
Import d'un PDF (POST /sources/file). Le texte est fourni par une doublure de lire_pages et les
embeddings sont simulés : on teste le type du fichier, le stockage et la pipeline.
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
from app.services import documents  # noqa: E402
from app.services.documents import decouper_pages, est_pdf  # noqa: E402
from app.services.video import pipeline  # noqa: E402

API = "/api/v1"
FAUX_PDF = b"%PDF-1.4\n% contenu de test\n%%EOF\n"


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
def fake_pdf(monkeypatch, tmp_path):
    """Dossier temporaire, texte de deux pages et embeddings simulés."""
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr("app.api.routes.sources.DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "lire_pages", lambda chemin: [
        (1, "La relativité restreinte décrit le mouvement à vitesse constante."),
        (2, "La relativité générale ajoute la gravitation à cette description."),
    ])
    monkeypatch.setattr(pipeline, "encoder_passages", lambda textes: [[0.1] * 8 for _ in textes])
    return tmp_path


# ---------- Vérification du type ----------

def test_est_pdf_regarde_le_contenu():
    assert est_pdf(b"%PDF-1.7 ...")
    assert not est_pdf(b"<html>")
    assert not est_pdf(b"")


def test_decouper_pages_etiquette_chaque_passage_par_page():
    passages = decouper_pages([(1, "Premier paragraphe."), (3, "Autre page.")])
    assert [p["timestamp"] for p in passages] == ["p. 1", "p. 3"]
    assert passages[0]["text"] == "Premier paragraphe."


# ---------- Route POST /sources/file ----------

def test_pdf_est_indexe(client, fake_pdf):
    r = client.post(f"{API}/sources/file?filename=cours.pdf", content=FAUX_PDF,
                    headers={**auth("u1"), "Content-Type": "application/pdf"})
    assert r.status_code == 202
    source_id = r.json()["id"]
    detail = client.get(f"{API}/sources/{source_id}", headers=auth("u1")).json()
    assert detail["status"] == "ready"
    assert detail["source_type"] == "pdf"
    assert detail["title"] == "cours"
    assert detail["chunk_count"] == 2
    assert (fake_pdf / f"{source_id}.pdf").exists()

    passages = client.get(f"{API}/sources/{source_id}/transcript", headers=auth("u1")).json()
    assert [p["timestamp"] for p in passages] == ["p. 1", "p. 2"]


def test_fichier_qui_n_est_pas_un_pdf_est_refuse(client, fake_pdf):
    r = client.post(f"{API}/sources/file?filename=cours.pdf", content=b"<html>pas un pdf</html>",
                    headers={**auth("u1"), "Content-Type": "application/pdf"})
    assert r.status_code == 415
    assert list(fake_pdf.iterdir()) == []  # le fichier refusé est supprimé


def test_mauvaise_extension_est_refusee(client, fake_pdf):
    r = client.post(f"{API}/sources/file?filename=cours.docx", content=FAUX_PDF, headers=auth("u1"))
    assert r.status_code == 415


def test_pdf_sans_texte_donne_une_erreur(client, fake_pdf, monkeypatch):
    monkeypatch.setattr(pipeline, "lire_pages", lambda chemin: [])
    r = client.post(f"{API}/sources/file?filename=scan.pdf", content=FAUX_PDF, headers=auth("u1"))
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "error"
    assert "Scanned" in detail["error"]


def test_pdf_reste_prive(client, fake_pdf):
    r = client.post(f"{API}/sources/file?filename=cours.pdf", content=FAUX_PDF, headers=auth("u1"))
    r2 = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u2"))
    assert r2.status_code == 404
