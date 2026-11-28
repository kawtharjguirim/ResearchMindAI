"""
Graphe de connaissances scientifique (Neo4j) : articles du corpus, références et auteurs.

Source : les fichiers .bib de data_latex/. Chaque article (identifiant arXiv) a son dossier, et
ses fichiers .bib listent sa bibliographie. On en tire :
  (Paper)-[:CITES]->(Reference)       une référence citée par un article du corpus
  (Author)-[:AUTHORED]->(Reference)   un auteur d'une référence

Le graphe décrit la littérature. Il est distinct du Research Twin, qui décrit votre projet.
"""
import logging
import re
from pathlib import Path

import bibtexparser

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Au-delà de cette taille, un .bib est une base bibliographique (ex. toutes les actes d'une conférence),
# pas la bibliographie d'un article : il est ignoré, et la lecture serait trop lente.
TAILLE_MAX_BIB = 5 * 1024**2

# backend/app/services/knowledge_graph.py -> racine du projet -> data_latex/data/tex
CORPUS_PAR_DEFAUT = Path(__file__).resolve().parents[3] / "data_latex" / "data" / "tex"


def _nettoyer(texte: str | None) -> str:
    """Retire les accolades LaTeX et les espaces superflus."""
    if not texte:
        return ""
    return " ".join(texte.replace("{", "").replace("}", "").split())


def _cle(titre: str, cle_bib: str) -> str:
    """Identifiant d'une référence : son titre normalisé (même article cité dans deux bibliographies = un nœud)."""
    normalise = re.sub(r"[\W_]+", " ", titre.lower()).strip()
    return normalise[:200] if normalise else cle_bib


def _auteurs(champ: str | None) -> list[str]:
    """Noms d'auteurs d'un champ BibTeX « A and B and C », sans les espaces ni les accolades."""
    if not champ:
        return []
    return [_nettoyer(nom) for nom in champ.split(" and ") if _nettoyer(nom)]


def lire_bib(chemin: Path) -> list[dict]:
    """Entrées d'un fichier .bib, réduites aux champs utiles."""
    # common_strings : les mois (« sept », « jan »…) sont des macros BibTeX standard.
    analyseur = bibtexparser.bparser.BibTexParser(common_strings=True)
    try:
        base = bibtexparser.loads(chemin.read_text(encoding="utf-8", errors="replace"), parser=analyseur)
    except Exception:  # noqa: BLE001 : un .bib mal formé ne doit pas bloquer le corpus
        logger.warning("Bibliographie ignorée (illisible) : %s", chemin)
        return []
    entrees = []
    for e in base.entries:
        titre = _nettoyer(e.get("title"))
        entrees.append({
            "cle": _cle(titre, e.get("ID", "")),
            "titre": titre,
            "annee": _nettoyer(e.get("year")),
            "journal": _nettoyer(e.get("journal") or e.get("booktitle")),
            "doi": _nettoyer(e.get("doi")),
            "arxiv": _nettoyer(e.get("eprint")),
            "auteurs": _auteurs(e.get("author")),
        })
    return entrees


def lire_corpus(dossier: Path = CORPUS_PAR_DEFAUT) -> list[dict]:
    """Articles du corpus : identifiant (dossier arXiv), domaine et références de leurs fichiers .bib."""
    articles: dict[str, dict] = {}
    for fichier in sorted(dossier.rglob("*.bib")):
        relatif = fichier.relative_to(dossier).parts
        if len(relatif) < 3:   # domaine / article / fichier.bib
            continue
        if fichier.stat().st_size > TAILLE_MAX_BIB:
            logger.warning("Bibliographie ignorée (trop volumineuse) : %s", fichier)
            continue
        domaine, identifiant = relatif[0], relatif[1]
        article = articles.setdefault(identifiant, {"id": identifiant, "domaine": domaine, "references": []})
        article["references"].extend(lire_bib(fichier))
    # Une référence citée deux fois dans le même article n'est comptée qu'une fois.
    for article in articles.values():
        vues, uniques = set(), []
        for ref in article["references"]:
            if ref["cle"] not in vues:
                vues.add(ref["cle"])
                uniques.append(ref)
        article["references"] = uniques
    return [a for a in articles.values() if a["references"]]


def requetes(articles: list[dict]) -> list[tuple[str, dict]]:
    """Requêtes Cypher (MERGE, donc sans doublon) qui reconstruisent le graphe depuis les articles."""
    papiers = [{"id": a["id"], "domaine": a["domaine"], "nb": len(a["references"])} for a in articles]
    references: dict[str, dict] = {}
    liens_cites, liens_auteurs, auteurs = [], [], set()
    for a in articles:
        for r in a["references"]:
            references.setdefault(r["cle"], {"cle": r["cle"], "titre": r["titre"], "annee": r["annee"],
                                             "journal": r["journal"], "doi": r["doi"], "arxiv": r["arxiv"]})
            liens_cites.append({"paper": a["id"], "cle": r["cle"]})
            for nom in r["auteurs"]:
                auteurs.add(nom)
                liens_auteurs.append({"nom": nom, "cle": r["cle"]})
    return [
        ("UNWIND $lignes AS l MERGE (p:Paper {id: l.id}) SET p.domaine = l.domaine, p.nb_references = l.nb",
         {"lignes": papiers}),
        ("UNWIND $lignes AS l MERGE (r:Reference {cle: l.cle}) "
         "SET r.titre = l.titre, r.annee = l.annee, r.journal = l.journal, r.doi = l.doi, r.arxiv = l.arxiv",
         {"lignes": list(references.values())}),
        ("UNWIND $lignes AS l MATCH (p:Paper {id: l.paper}) MATCH (r:Reference {cle: l.cle}) "
         "MERGE (p)-[:CITES]->(r)", {"lignes": liens_cites}),
        ("UNWIND $lignes AS l MERGE (a:Author {nom: l.nom})", {"lignes": [{"nom": n} for n in sorted(auteurs)]}),
        ("UNWIND $lignes AS l MATCH (a:Author {nom: l.nom}) MATCH (r:Reference {cle: l.cle}) "
         "MERGE (a)-[:AUTHORED]->(r)", {"lignes": liens_auteurs}),
    ]


def pilote():
    """Connexion à Neo4j, avec les réglages de backend/.env."""
    from neo4j import GraphDatabase
    reglages = get_settings()
    return GraphDatabase.driver(reglages.neo4j_uri, auth=(reglages.neo4j_user, reglages.neo4j_password))


def construire(articles: list[dict], driver) -> dict:
    """Écrit le graphe dans Neo4j et renvoie les effectifs."""
    with driver.session() as session:
        for cypher, parametres in requetes(articles):
            session.run(cypher, parametres).consume()
    return statistiques(driver)


def statistiques(driver) -> dict:
    """Nombre de nœuds par type et de relations par type."""
    with driver.session() as session:
        noeuds = {r["label"]: r["n"] for r in session.run(
            "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS n")}
        relations = {r["type"]: r["n"] for r in session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n")}
    return {"noeuds": noeuds, "relations": relations}


# Type d'entité → nœud et type de relation. Les relations suivent le schéma du plan :
# un article USES une méthode ou un jeu de données, et EVALUATES un résultat.
ENTITES = {
    "Method": ("Method", "USES"),
    "Dataset": ("Dataset", "USES"),
    "Result": ("Result", "EVALUATES"),
    "Concept": ("Concept", "MENTIONS"),
}


def ajouter_proposition(driver, proposition: dict, owner: str) -> None:
    """
    Écrit une proposition approuvée dans Neo4j, avec sa provenance sur la relation.
    Appelé uniquement après approbation par l'utilisateur. Les entités et relations portent le
    propriétaire (owner) : un utilisateur ne voit pas les propositions des autres.
    """
    etiquette, relation = ENTITES[proposition["entity_type"]]
    cle = proposition["document_key"]
    if cle.startswith("corpus:"):
        # Même nœud Paper que pour le graphe des bibliographies.
        document = "MERGE (d:Paper {id: $doc_id}) SET d.titre = $titre"
        doc_id = cle.split(":", 1)[1]
    else:
        document = "MERGE (d:Document {cle: $doc_id}) SET d.titre = $titre"
        doc_id = cle
    cypher = (
        f"{document} "
        f"MERGE (e:{etiquette} {{nom_normal: $nom_normal, owner: $owner}}) SET e.nom = $nom "
        f"MERGE (d)-[r:{relation} {{owner: $owner, location: $location}}]->(e) "
        "SET r.phrase = $phrase, r.verification = $verification, r.date = $date, r.document_key = $cle"
    )
    parametres = {
        "doc_id": doc_id, "titre": proposition["document_title"], "owner": owner,
        "nom_normal": proposition["normalized_name"], "nom": proposition["name"],
        "location": proposition["location"], "phrase": proposition["excerpt"],
        "verification": proposition["verification_status"], "date": proposition["extraction_date"],
        "cle": cle,
    }
    with driver.session() as session:
        session.run(cypher, parametres).consume()


def vue_utilisateur(driver, owner: str, limite: int = 300) -> dict:
    """
    Graphe validé d'un utilisateur, pour l'affichage : documents, entités approuvées et relations.
    Chaque relation garde sa provenance (phrase, page, document). Les bibliographies (étape 1)
    ne sont pas incluses : elles comptent des dizaines de milliers de nœuds.
    """
    cypher = (
        "MATCH (d)-[r]->(e) WHERE r.owner = $owner AND type(r) IN ['USES', 'EVALUATES', 'MENTIONS'] "
        "RETURN coalesce(d.id, d.cle) AS d_id, coalesce(d.titre, d.id, d.cle) AS d_titre, "
        "labels(e)[0] AS e_type, e.nom_normal AS e_id, e.nom AS e_nom, type(r) AS relation, "
        "r.phrase AS phrase, r.location AS location, r.document_key AS document_key "
        "LIMIT $limite"
    )
    noeuds: dict[str, dict] = {}
    liens: list[dict] = []
    with driver.session() as session:
        for ligne in session.run(cypher, {"owner": owner, "limite": limite}):
            doc = f"doc:{ligne['d_id']}"
            entite = f"{ligne['e_type']}:{ligne['e_id']}"
            noeuds.setdefault(doc, {"id": doc, "type": "Document", "label": ligne["d_titre"],
                                    "document_key": ligne["document_key"]})
            noeuds.setdefault(entite, {"id": entite, "type": ligne["e_type"], "label": ligne["e_nom"]})
            liens.append({"source": doc, "target": entite, "relation": ligne["relation"],
                          "phrase": ligne["phrase"], "location": ligne["location"],
                          "document_key": ligne["document_key"]})
    return {"nodes": list(noeuds.values()), "edges": liens}
