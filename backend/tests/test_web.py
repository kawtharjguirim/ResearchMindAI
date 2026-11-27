"""
Import d'une page web (POST /sources/url). Le réseau est remplacé par une page HTML fixe ; on teste
la sécurité des adresses, l'extraction du texte, le découpage et les statuts.
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
from app.services.video import pipeline  # noqa: E402
from app.services.web import WebError, decouper, extraire_texte, verifier_url  # noqa: E402

API = "/api/v1"

PARAGRAPHE = ("La relativité restreinte décrit comment les mesures d'espace et de temps dépendent "
              "du mouvement de l'observateur, à vitesse constante, sans gravitation. ")
PAGE = f"""<!doctype html><html><head><title>Relativité restreinte</title></head><body>
<nav>Accueil | Contact</nav>
<article><h1>Relativité restreinte</h1>
{''.join(f'<p>{PARAGRAPHE * 3}</p>' for _ in range(8))}
</article><footer>Mentions légales</footer></body></html>"""


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
def fake_web(monkeypatch):
    """Page HTML et embeddings simulés : aucun accès réseau, aucun modèle chargé."""
    monkeypatch.setattr(pipeline, "telecharger_html",
                        lambda url: ("https://exemple.org/relativite", PAGE))
    monkeypatch.setattr(pipeline, "encoder_passages", lambda textes: [[0.1] * 8 for _ in textes])


# ---------- Sécurité des adresses ----------

@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",
    "http://localhost:8000/api/v1/health",
    "http://192.168.1.1/",
    "http://10.0.0.5/",
    "http://169.254.169.254/latest/meta-data",
])
def test_adresses_internes_refusees(url):
    with pytest.raises(WebError, match="non publique"):
        verifier_url(url)


@pytest.mark.parametrize("url", ["ftp://exemple.org/x", "exemple.org", "file:///etc/passwd"])
def test_schemas_refuses(url):
    with pytest.raises(WebError, match="http"):
        verifier_url(url)


# ---------- Extraction et découpage ----------

def test_extraction_garde_le_texte_principal():
    titre, texte = extraire_texte(PAGE, "https://exemple.org/relativite")
    assert titre == "Relativité restreinte"
    assert "relativité restreinte" in texte.lower()
    assert "Mentions légales" not in texte


def test_decouper_regroupe_les_paragraphes():
    texte = "\n".join(["mot " * 80 for _ in range(6)])  # 6 paragraphes de 80 mots
    passages = decouper(texte, max_mots=200)
    assert len(passages) == 3                         # 2 paragraphes par passage
    assert passages[0]["timestamp"] == "§ 1"
    assert passages[0]["start"] == 0.0 and passages[0]["end"] == 0.0


# ---------- Route POST /sources/url ----------

def test_page_web_est_indexee(client, fake_web):
    r = client.post(f"{API}/sources/url", json={"url": "https://exemple.org/relativite"}, headers=auth("u1"))
    assert r.status_code == 202
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "ready"
    assert detail["source_type"] == "web"
    assert detail["url"] == "https://exemple.org/relativite"
    assert detail["title"] == "Relativité restreinte"  # titre de la page remplace le nom de domaine
    assert detail["chunk_count"] >= 1


def test_page_sans_texte_donne_une_erreur(client, monkeypatch):
    monkeypatch.setattr(pipeline, "telecharger_html", lambda url: (url, "<html><body></body></html>"))
    monkeypatch.setattr(pipeline, "encoder_passages", lambda textes: [[0.1] * 8 for _ in textes])
    r = client.post(f"{API}/sources/url", json={"url": "https://exemple.org/vide"}, headers=auth("u1"))
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "error"
    assert detail["error"] == "Aucun texte exploitable sur cette page."


def test_adresse_interne_refusee_a_l_import(client):
    r = client.post(f"{API}/sources/url", json={"url": "http://127.0.0.1:8000/api/v1/health"}, headers=auth("u1"))
    assert r.status_code == 400
    assert "non publique" in r.json()["detail"]
