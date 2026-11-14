"""Routes /evaluation : relecture du jeu de test, sur une copie temporaire du fichier."""
import json
import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_researchmind.db")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-with-enough-length-for-hs256!")

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes import evaluation  # noqa: E402
from app.main import app  # noqa: E402

API = "/api/v1"


def auth(sub: str = "alice") -> dict:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {jwt.encode(payload, os.environ['SUPABASE_JWT_SECRET'], 'HS256')}"}


QUESTION = {"id": "biologie-01", "domaine": "biologie", "split": "test", "document_id": "2204.13048",
            "chunk_id": "2204.13048_0015", "question": "Comment fonctionne le Matches Condenser ?",
            "reference": "Par attention.", "question_initiale": "Comment fonctionne le Matches Condenser ?",
            "reference_initiale": "Par attention.", "auteur": "claude", "statut": "a_valider", "commentaire": ""}


@pytest.fixture
def jeu(monkeypatch, tmp_path):
    (tmp_path / "jeu_corpus.json").write_text(json.dumps({"questions": [QUESTION]}), encoding="utf-8")
    (tmp_path / "passages_echantillon.json").write_text(json.dumps([{
        "chunk_id": "2204.13048_0015", "titre": "TERMinator", "section": "Matches Condenser",
        "texte": "The Matches Condenser serves to compress..."}]), encoding="utf-8")
    monkeypatch.setattr(evaluation, "EVAL_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_requires_token(client, jeu):
    assert client.get(f"{API}/evaluation/questions").status_code == 401


def test_list_includes_the_targeted_passage(client, jeu):
    r = client.get(f"{API}/evaluation/questions", headers=auth())
    assert r.status_code == 200
    q = r.json()[0]
    assert q["titre"] == "TERMinator" and q["passage"].startswith("The Matches Condenser")


def test_correction_is_written_to_the_file(client, jeu):
    r = client.patch(f"{API}/evaluation/questions/biologie-01", headers=auth(),
                     json={"statut": "corrige", "question": "  Que fait le Matches Condenser de TERMinator ?  "})
    assert r.status_code == 200 and r.json()["statut"] == "corrige"
    saved = json.loads((jeu / "jeu_corpus.json").read_text(encoding="utf-8"))["questions"][0]
    assert saved["question"] == "Que fait le Matches Condenser de TERMinator ?"
    assert saved["question_initiale"] == QUESTION["question"]


def test_invalid_status_and_unknown_id_are_rejected(client, jeu):
    assert client.patch(f"{API}/evaluation/questions/biologie-01", headers=auth(),
                        json={"statut": "peut-etre"}).status_code == 422
    assert client.patch(f"{API}/evaluation/questions/inconnue", headers=auth(),
                        json={"statut": "valide"}).status_code == 404
