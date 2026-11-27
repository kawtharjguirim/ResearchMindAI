"""
Import d'un lien YouTube (POST /sources/url). L'accès réseau à YouTube et les modèles
d'embeddings sont remplacés par des doublures : on teste l'extraction de l'identifiant,
la pipeline et les statuts d'erreur.
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
from app.services.video.youtube import YouTubeError, extraire_id  # noqa: E402

API = "/api/v1"
ID = "dQw4w9WgXcQ"
SEGMENTS = [
    {"start": 0.0, "end": 4.0, "text": "Le GPS doit corriger l'effet de la relativité."},
    {"start": 4.0, "end": 9.0, "text": "Sans cette correction, la position dériverait."},
    {"start": 60.0, "end": 70.0, "text": "Passons maintenant à la cuisine italienne."},
]


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
def fake_youtube(monkeypatch):
    """Sous-titres et embeddings simulés : aucun appel à YouTube ni chargement de modèle."""
    monkeypatch.setattr(pipeline, "recuperer_segments", lambda video_id, langue: (SEGMENTS, "fr"))
    monkeypatch.setattr(pipeline, "encoder_passages", lambda textes: [[0.1] * 8 for _ in textes])


# ---------- Extraction de l'identifiant ----------

@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={ID}",
    f"https://youtube.com/watch?v={ID}&t=42s",
    f"https://m.youtube.com/watch?feature=share&v={ID}",
    f"https://youtu.be/{ID}",
    f"https://www.youtube.com/shorts/{ID}",
    f"youtube.com/embed/{ID}",
])
def test_extraire_id_accepte_les_formes_courantes(url):
    assert extraire_id(url) == ID


@pytest.mark.parametrize("url", [
    "https://example.com/watch?v=" + ID,
    "https://www.youtube.com/watch?v=trop-court",
    "https://www.youtube.com/@chaine",
    "https://www.youtube.com/",
    "pas une url",
    "",
])
def test_extraire_id_refuse_les_autres_liens(url):
    assert extraire_id(url) is None


# ---------- Route POST /sources/url ----------

def test_lien_invalide_renvoie_400(client):
    r = client.post(f"{API}/sources/url", json={"url": "ftp://example.com/page"}, headers=auth("u1"))
    assert r.status_code == 400


def test_import_youtube_est_indexe(client, fake_youtube):
    r = client.post(f"{API}/sources/url", json={"url": f"https://youtu.be/{ID}", "title": "Test"},
                    headers=auth("u1"))
    assert r.status_code == 202
    body = r.json()
    # La tâche de fond tourne avant la fin de la requête de test : la source est déjà prête.
    detail = client.get(f"{API}/sources/{body['id']}", headers=auth("u1")).json()
    assert detail["status"] == "ready"
    assert detail["url"] == f"https://www.youtube.com/watch?v={ID}"
    assert detail["language"] == "fr"
    assert detail["chunk_count"] >= 1
    assert detail["duration"] == 70.0


def test_sous_titres_absents_donnent_une_erreur_lisible(client, monkeypatch):
    def pas_de_sous_titres(video_id, langue):
        raise YouTubeError("Cette vidéo n'a pas de sous-titres (ils sont désactivés par son auteur).")

    monkeypatch.setattr(pipeline, "recuperer_segments", pas_de_sous_titres)
    r = client.post(f"{API}/sources/url", json={"url": f"https://youtu.be/{ID}"}, headers=auth("u1"))
    detail = client.get(f"{API}/sources/{r.json()['id']}", headers=auth("u1")).json()
    assert detail["status"] == "error"
    # Pas de préfixe technique devant le message destiné à l'utilisateur.
    assert detail["error"] == "Cette vidéo n'a pas de sous-titres (ils sont désactivés par son auteur)."


def test_import_youtube_reste_prive(client, fake_youtube):
    r = client.post(f"{API}/sources/url", json={"url": f"https://youtu.be/{ID}"}, headers=auth("u1"))
    source_id = r.json()["id"]
    r2 = client.get(f"{API}/sources/{source_id}", headers=auth("u2"))
    assert r2.status_code == 404
