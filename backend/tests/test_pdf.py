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


# ---------- Images (OCR) ----------

FAUSSE_IMAGE = b"\x89PNG\r\n\x1a\n" + b"contenu de test"


def test_image_est_indexee_par_ocr(client, fake_pdf, monkeypatch):
    monkeypatch.setattr(pipeline, "lire_texte_image", lambda chemin: ["Diabetic retinopathy detection", "Transformers"])
    r = client.post(f"{API}/sources/file?filename=schema.png", content=FAUSSE_IMAGE, headers=auth("u1"))
    assert r.status_code == 202
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "ready"
    assert detail["source_type"] == "figure"
    passages = client.get(f"{API}/sources/{r.json()['id']}/transcript", headers=auth("u1")).json()
    assert passages[0]["timestamp"] == "image"
    assert "retinopathy" in passages[0]["text"]


def test_image_sans_texte_donne_une_erreur(client, fake_pdf, monkeypatch):
    monkeypatch.setattr(pipeline, "lire_texte_image", lambda chemin: [])
    r = client.post(f"{API}/sources/file?filename=photo.jpg", content=b"\xff\xd8\xff\xe0test", headers=auth("u1"))
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "error"
    assert "No readable text" in detail["error"]


def test_contenu_ne_correspond_pas_a_l_extension(client, fake_pdf):
    r = client.post(f"{API}/sources/file?filename=image.png", content=FAUX_PDF, headers=auth("u1"))
    assert r.status_code == 415


def test_etiquettes_parasites_ecartees():
    from app.services.documents import decouper_image
    passages = decouper_image(["RETRIEVAL", ".", "+", "|", "a", "Vector DB", "ab"])
    assert [p["text"] for p in passages] == ["RETRIEVAL", "Vector DB", "ab"]


def test_lignes_parasites_ecartees_dans_un_pdf():
    passages = decouper_pages([(1, "3\n.\nLa relativité restreinte décrit le mouvement.\n•\n"), (2, "7")])
    assert len(passages) == 1
    assert "+" not in passages[0]["text"] and passages[0]["text"] == "La relativité restreinte décrit le mouvement."
    assert passages[0]["timestamp"] == "p. 1"


def test_bibliographie_detectee_sans_toucher_au_texte_normal():
    from app.services.documents import est_bibliographie
    assert est_bibliographie("[63] N. Raj, P. Tanedo. [64] M. Cirelli, N. Fornengo, 2006")
    assert not est_bibliographie("Dark matter capture in white dwarves depends on the particle mass.")


def test_resume_passe_en_premier():
    from app.services.documents import decouper_pages
    texte_resume = "Weakly Interacting Massive Particles can be captured in compact stars " * 3
    pages = [(1, "Titre de l'article\nAuteurs"), (2, "Abstract. " + texte_resume + "\n1 Introduction\nLe texte du corps.")]
    passages = decouper_pages(pages)
    assert passages[0]["timestamp"] == "p. 2 (abstract)"
    assert "Weakly Interacting" in passages[0]["text"]
    assert "Le texte du corps" in " ".join(p["text"] for p in passages[1:])
