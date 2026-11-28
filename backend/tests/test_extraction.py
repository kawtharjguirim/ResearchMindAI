"""
Extraction d'entités : contrôle déterministe, sélection des passages, extraction et routes.
Le LLM est remplacé par une doublure qui renvoie des réponses fixées par le test ; les textes sont
des données de test fictives, sans valeur scientifique.
"""
import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_researchmind.db")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-with-enough-length-for-hs256!")

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.knowledge import KnowledgeProposal  # noqa: E402
from app.services import extraction, knowledge_graph as kg  # noqa: E402
from app.services.video import llm  # noqa: E402

API = "/api/v1"
PASSAGE_TEST = ("Dans ce document de test, le modèle FictifNet est évalué sur le jeu de données JeuTest. "
                "Son score de précision atteint 0,91 sur la partie de validation, selon les mesures fictives. ") * 2


def auth(sub: str) -> dict:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {jwt.encode(payload, os.environ['SUPABASE_JWT_SECRET'], 'HS256')}"}


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# ---------- Contrôle déterministe ----------

def test_phrase_exacte_et_nom_dans_la_phrase_est_verifiee():
    entite = {"type": "Method", "nom": "FictifNet",
              "phrase": "le modèle FictifNet est évalué sur le jeu de données JeuTest"}
    assert extraction.verifier(entite, PASSAGE_TEST) == extraction.VERIFIED


def test_phrase_inventee_est_rejetee():
    entite = {"type": "Result", "nom": "score", "phrase": "le modèle atteint 99 pour cent de précision partout"}
    assert extraction.verifier(entite, PASSAGE_TEST) == extraction.REJECTED


def test_phrase_proche_est_a_relire():
    # Une virgule et un mot de plus : la phrase n'est pas exacte, mais presque tous ses mots sont là.
    entite = {"type": "Result", "nom": "précision",
              "phrase": "son score de précision atteint 0,91 sur la partie de validation stable"}
    assert extraction.verifier(entite, PASSAGE_TEST) == extraction.NEEDS_REVIEW


def test_nom_absent_de_la_phrase_est_a_relire():
    # La phrase est dans le passage, mais le nom « AutreJeu » n'y figure pas : à relire.
    entite = {"type": "Dataset", "nom": "AutreJeu",
              "phrase": "le modèle FictifNet est évalué sur le jeu de données JeuTest"}
    assert extraction.verifier(entite, PASSAGE_TEST) == extraction.NEEDS_REVIEW


def test_champs_vides_sont_rejetes():
    assert extraction.verifier({"type": "Method", "nom": "", "phrase": "x"}, PASSAGE_TEST) == extraction.REJECTED


def test_normalisation_ignore_accents_et_ponctuation():
    assert extraction.normaliser("Relativité, RESTREINTE !") == "relativite restreinte"


# ---------- Sélection des passages ----------

def test_selection_ecarte_references_et_passages_courts():
    references = "[1] A. Dupont, Titre, 2020. [2] B. Martin, Autre, 2021. [3] C. Durand, 2019 et al."
    passages = [
        {"text": "court", "location": "p. 1"},
        {"text": PASSAGE_TEST, "location": "p. 2"},
        {"text": " ".join(["mot"] * 30) + " " + references, "location": "p. 9"},
    ]
    selection = extraction.selectionner(passages)
    assert [p["location"] for p in selection] == ["p. 2"]


# ---------- Extraction avec LLM simulé ----------

def reponse_llm(entites):
    def faux_chat(messages, schema=None, appels=None, etape=None):
        return {"entites": entites}
    return faux_chat


def test_extraire_document_enregistre_et_dedoublonne(monkeypatch):
    monkeypatch.setattr(llm, "chat", reponse_llm([
        {"type": "Method", "nom": "FictifNet", "phrase": "le modèle FictifNet est évalué sur le jeu de données JeuTest"},
        {"type": "Result", "nom": "score", "phrase": "une phrase inventée qui n'est pas dans le passage du tout"},
    ]))
    passages = [{"text": PASSAGE_TEST, "location": "p. 2"}]
    with SessionLocal() as db:
        bilan = extraction.extraire_document(db, "u1", "source:test", "Document de test", passages)
        assert bilan["proposees"] == 1
        assert bilan["rejetees"] == 1
        # Relance : la même proposition n'est pas ajoutée une seconde fois.
        bilan2 = extraction.extraire_document(db, "u1", "source:test", "Document de test", passages)
        assert bilan2["proposees"] == 0
        assert bilan2["doublons"] == 1
        lignes = db.scalars(select(KnowledgeProposal)).all()
        assert len(lignes) == 1
        assert lignes[0].verification_status == extraction.VERIFIED
        assert lignes[0].status == "pending"


def test_extraire_document_ne_touche_pas_aux_autres_utilisateurs(monkeypatch):
    monkeypatch.setattr(llm, "chat", reponse_llm([
        {"type": "Method", "nom": "FictifNet", "phrase": "le modèle FictifNet est évalué sur le jeu de données JeuTest"}]))
    passages = [{"text": PASSAGE_TEST, "location": "p. 2"}]
    with SessionLocal() as db:
        extraction.extraire_document(db, "u1", "source:test", "Doc", passages)
        bilan = extraction.extraire_document(db, "u2", "source:test", "Doc", passages)
        assert bilan["proposees"] == 1   # l'utilisateur u2 obtient ses propres propositions


# ---------- Routes : validation, rejet, isolation ----------

class PiloteFictif:
    """Remplace Neo4j : enregistre les écritures sans connexion réelle."""
    ecritures: list = []

    def session(self):
        pilote = self

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def run(self, cypher, parametres):
                pilote.ecritures.append((cypher, parametres))

                class R:
                    def consume(self):
                        return None
                return R()
        return Session()

    def close(self):
        return None


@pytest.fixture
def proposition():
    with SessionLocal() as db:
        p = KnowledgeProposal(user_id="u1", document_key="corpus:2100.00001", document_title="arXiv:2100.00001",
                              entity_type="Method", name="FictifNet", normalized_name="fictifnet",
                              excerpt="le modèle FictifNet est évalué", location="p. 2",
                              verification_status="VERIFIED", status="pending")
        db.add(p)
        db.commit()
        return p.id


def test_approuver_ecrit_dans_neo4j_et_passe_approved(proposition, monkeypatch):
    pilote = PiloteFictif()
    PiloteFictif.ecritures = []
    monkeypatch.setattr(kg, "pilote", lambda: pilote)
    client = TestClient(app)
    r = client.post(f"{API}/knowledge/proposals/{proposition}/approve", headers=auth("u1"))
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    assert len(PiloteFictif.ecritures) == 1
    cypher, parametres = PiloteFictif.ecritures[0]
    assert "USES" in cypher and "MERGE" in cypher
    assert parametres["owner"] == "u1"
    assert parametres["phrase"] == "le modèle FictifNet est évalué"   # la preuve est conservée
    # Une seconde approbation est refusée : pas de double écriture.
    r2 = client.post(f"{API}/knowledge/proposals/{proposition}/approve", headers=auth("u1"))
    assert r2.status_code == 409


def test_rejeter_n_ecrit_rien(proposition, monkeypatch):
    PiloteFictif.ecritures = []
    monkeypatch.setattr(kg, "pilote", lambda: PiloteFictif())
    client = TestClient(app)
    r = client.post(f"{API}/knowledge/proposals/{proposition}/reject", headers=auth("u1"))
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
    assert PiloteFictif.ecritures == []


def test_proposition_d_un_autre_utilisateur_est_introuvable(proposition, monkeypatch):
    monkeypatch.setattr(kg, "pilote", lambda: PiloteFictif())
    client = TestClient(app)
    r = client.post(f"{API}/knowledge/proposals/{proposition}/approve", headers=auth("u2"))
    assert r.status_code == 404


def test_approuver_sans_neo4j_laisse_la_proposition_en_attente(proposition, monkeypatch):
    def pilote_indisponible():
        raise ConnectionError("refusé")
    monkeypatch.setattr(kg, "pilote", pilote_indisponible)
    client = TestClient(app)
    r = client.post(f"{API}/knowledge/proposals/{proposition}/approve", headers=auth("u1"))
    assert r.status_code == 503
    en_attente = client.get(f"{API}/knowledge/proposals", headers=auth("u1")).json()
    assert [p["id"] for p in en_attente] == [proposition]


def test_liste_et_historique(proposition, monkeypatch):
    monkeypatch.setattr(kg, "pilote", lambda: PiloteFictif())
    client = TestClient(app)
    assert len(client.get(f"{API}/knowledge/proposals", headers=auth("u1")).json()) == 1
    assert client.get(f"{API}/knowledge/history", headers=auth("u1")).json() == []
    client.post(f"{API}/knowledge/proposals/{proposition}/reject", headers=auth("u1"))
    assert len(client.get(f"{API}/knowledge/history", headers=auth("u1")).json()) == 1


def test_meme_entite_deux_fois_dans_un_passage_donne_une_proposition(monkeypatch):
    # Régression : le LLM cite deux fois la même entité dans un passage ; une seule proposition, sans erreur.
    entite = {"type": "Method", "nom": "FictifNet", "phrase": "le modèle FictifNet est évalué sur le jeu de données JeuTest"}
    monkeypatch.setattr(llm, "chat", reponse_llm([entite, dict(entite)]))
    with SessionLocal() as db:
        bilan = extraction.extraire_document(db, "u-regr", "corpus:regr", "Regression", [{"text": PASSAGE_TEST, "location": "p. 1"}])
        assert bilan["proposees"] == 1
        assert bilan["doublons"] == 1
        assert len(db.scalars(select(KnowledgeProposal).where(KnowledgeProposal.user_id == "u-regr")).all()) == 1


@pytest.mark.parametrize("nom", ["QAHE", "square lattice", "ferromagnetic semiconductor", "ARPES"])
def test_nom_utile_garde_les_noms_informatifs(nom):
    assert extraction.nom_utile(nom)


@pytest.mark.parametrize("nom", ["", "Γ X Y M", "β/b 1", "(γ + η)/a 3", "M", "ab", "1 2 3",
                                 "une phrase entière qui décrit longuement le résultat obtenu dans le passage et au-delà de quatre-vingts caractères"])
def test_nom_utile_ecarte_les_fragments(nom):
    assert not extraction.nom_utile(nom)


def test_forme_canonique_regroupe_acronyme_et_forme_complete():
    alias: dict[str, str] = {}
    assert extraction.forme_canonique("quantum anomalous Hall effect (QAHE)", alias) == "qahe"
    assert extraction.forme_canonique("QAHE", alias) == "qahe"
    # Une forme complète vue ensuite, sans acronyme, rejoint l'acronyme déjà connu.
    assert extraction.forme_canonique("Quantum anomalous Hall effect", alias) == "qahe"
    assert extraction.forme_canonique("square lattice", alias) == "square lattice"


def test_acronyme_et_forme_complete_dans_un_meme_passage_donnent_une_proposition(monkeypatch):
    monkeypatch.setattr(llm, "chat", reponse_llm([
        {"type": "Concept", "nom": "quantum anomalous Hall effect (QAHE)",
         "phrase": "le modèle FictifNet est évalué sur le jeu de données JeuTest"},
        {"type": "Concept", "nom": "QAHE",
         "phrase": "le modèle FictifNet est évalué sur le jeu de données JeuTest"},
    ]))
    with SessionLocal() as db:
        bilan = extraction.extraire_document(db, "u-acro", "corpus:acro", "Acronymes",
                                             [{"text": PASSAGE_TEST, "location": "p. 1"}])
        assert bilan["proposees"] == 1
        assert bilan["doublons"] == 1
