"""
Graphe de connaissances : lecture des .bib et requêtes Cypher. Données de test isolées, fictives,
fournies ici uniquement pour tester le code. Aucun appel à Neo4j.
"""
from pathlib import Path

import pytest

from app.services import knowledge_graph as kg

BIB_TEST = """
@article{cle_test_1,
  title={Un {CNN} de test pour l'imagerie},
  author={Dupont, Ana and Martin Bob},
  journal={Revue de test},
  year={2020},
  month=sep,
  doi={10.0000/test.1}
}

@inproceedings{cle_test_2,
  title={Un CNN de test pour l imagerie},
  author={Dupont, Ana},
  booktitle={Conférence de test},
  year={2021}
}
"""


def ecrire(dossier: Path, relatif: str, contenu: str) -> Path:
    chemin = dossier / relatif
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_lire_bib_extrait_champs_et_auteurs(tmp_path):
    entrees = kg.lire_bib(ecrire(tmp_path, "a.bib", BIB_TEST))
    assert len(entrees) == 2
    premiere = entrees[0]
    assert premiere["titre"] == "Un CNN de test pour l'imagerie"   # accolades retirées
    assert premiere["annee"] == "2020"
    assert premiere["journal"] == "Revue de test"
    assert premiere["doi"] == "10.0000/test.1"
    assert premiere["auteurs"] == ["Dupont, Ana", "Martin Bob"]


def test_lire_bib_mois_standard_sans_erreur(tmp_path):
    # Le mois « sep » est une macro BibTeX standard : elle ne doit pas faire échouer la lecture.
    entrees = kg.lire_bib(ecrire(tmp_path, "b.bib", BIB_TEST))
    assert entrees[0]["titre"]


def test_lire_bib_fichier_mal_forme_est_ignore(tmp_path):
    chemin = ecrire(tmp_path, "casse.bib", "@article{ (((")
    assert isinstance(kg.lire_bib(chemin), list)


def test_lire_corpus_regroupe_par_article_et_deduplique(tmp_path):
    ecrire(tmp_path, "informatique/2100.00001/references.bib", BIB_TEST)
    ecrire(tmp_path, "informatique/2100.00001/autre.bib", BIB_TEST)   # même référence deux fois
    ecrire(tmp_path, "biologie/2100.00002/refs.bib", BIB_TEST)
    articles = {a["id"]: a for a in kg.lire_corpus(tmp_path)}
    assert set(articles) == {"2100.00001", "2100.00002"}
    assert articles["2100.00001"]["domaine"] == "informatique"
    # Mêmes titres (normalisés) dans tous les fichiers : une seule référence pour cet article.
    assert len(articles["2100.00001"]["references"]) == 1


def test_requetes_sont_idempotentes_MERGE(tmp_path):
    articles = [{"id": "2100.00001", "domaine": "informatique", "references": [
        {"cle": "un cnn de test pour l imagerie", "titre": "Un CNN de test", "annee": "2020",
         "journal": "Revue", "doi": "", "arxiv": "", "auteurs": ["Dupont, Ana"]}]}]
    requetes = kg.requetes(articles)
    cyphers = [c for c, _ in requetes]
    assert all("MERGE" in c for c in cyphers)               # pas de doublon à chaque relance
    assert any("CITES" in c for c in cyphers)
    assert any("AUTHORED" in c for c in cyphers)
    parametres_papiers = requetes[0][1]["lignes"]
    assert parametres_papiers == [{"id": "2100.00001", "domaine": "informatique", "nb": 1}]


def test_requetes_ne_creent_pas_de_reference_en_double(tmp_path):
    ref = {"cle": "meme", "titre": "Meme", "annee": "", "journal": "", "doi": "", "arxiv": "", "auteurs": []}
    articles = [{"id": "p1", "domaine": "d", "references": [ref]},
                {"id": "p2", "domaine": "d", "references": [ref]}]
    references = kg.requetes(articles)[1][1]["lignes"]
    assert len(references) == 1
    liens = kg.requetes(articles)[2][1]["lignes"]
    assert len(liens) == 2                                   # deux articles citent la même référence


def test_construire_appelle_chaque_requete(monkeypatch):
    appels = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def run(self, cypher, parametres):
            appels.append(cypher)

            class Resultat:
                def consume(self):
                    return None
            return Resultat()

    class Pilote:
        def session(self):
            return Session()

    monkeypatch.setattr(kg, "statistiques", lambda driver: {"noeuds": {}, "relations": {}})
    articles = [{"id": "p1", "domaine": "d", "references": [
        {"cle": "r1", "titre": "R1", "annee": "", "journal": "", "doi": "", "arxiv": "", "auteurs": ["A"]}]}]
    resultat = kg.construire(articles, Pilote())
    assert len(appels) == 5
    assert resultat == {"noeuds": {}, "relations": {}}


def test_lire_corpus_ignore_les_bases_trop_volumineuses(tmp_path, monkeypatch):
    monkeypatch.setattr(kg, "TAILLE_MAX_BIB", 100)   # seuil abaissé pour le test
    ecrire(tmp_path, "informatique/2100.00003/grosse.bib", BIB_TEST * 10)
    ecrire(tmp_path, "informatique/2100.00004/petit.bib", BIB_TEST[:120] + "\n}\n")
    ids = {a["id"] for a in kg.lire_corpus(tmp_path)}
    assert "2100.00003" not in ids
