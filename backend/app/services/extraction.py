"""
Extraction d'entités scientifiques depuis les passages d'un document, avec preuve exacte.

Le LLM (qwen2.5:3b via Ollama) propose des entités et la phrase qui les mentionne. Un contrôle
déterministe, qui ne dépend pas du LLM, décide ensuite si la proposition est vérifiable :
  VERIFIED      : la phrase est dans le passage et le nom est dans la phrase ;
  NEEDS_REVIEW  : la phrase est proche du passage (mots presque tous présents) : à relire ;
  REJECTED      : la phrase n'est pas dans le passage : elle n'est jamais proposée.
Une relation n'est jamais considérée comme vérifiée parce que le LLM l'a générée.
"""
import logging
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeProposal
from app.services.documents import est_bibliographie
from app.services.video import llm

logger = logging.getLogger(__name__)

TYPES = ("Method", "Dataset", "Result", "Concept")
VERIFIED, NEEDS_REVIEW, REJECTED = "VERIFIED", "NEEDS_REVIEW", "REJECTED"
MOTS_MINIMUM = 25        # un passage plus court ne contient en général pas d'information exploitable
PASSAGES_MAXIMUM = 40    # plafond par document, pour limiter le temps de calcul sur CPU
SEUIL_PROCHE = 0.8       # part des mots de la phrase présents dans le passage
LONGUEUR_NOM_MAXIMUM = 80  # au-delà, ce n'est plus un nom mais une phrase

SCHEMA = {
    "type": "object",
    "properties": {
        "entites": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": list(TYPES)},
                    "nom": {"type": "string"},
                    "phrase": {"type": "string"},
                },
                "required": ["type", "nom", "phrase"],
            },
        }
    },
    "required": ["entites"],
}

SYSTEME = (
    "Tu extrais des informations scientifiques d'un passage. Règles : n'utilise que le passage. "
    "Pour chaque élément, donne son nom tel qu'il apparaît, et la phrase exacte, copiée mot pour mot "
    "du passage, qui le mentionne. N'invente rien : si le passage ne contient rien d'utile, renvoie une "
    "liste vide. Types : Method (méthode ou algorithme), Dataset (jeu de données), Result (résultat "
    "chiffré ou constat), Concept (notion scientifique importante)."
)


def normaliser(texte: str) -> str:
    """Minuscules, sans accents ni ponctuation, espaces réduits : sert à comparer les textes."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sans_accents.lower()).split())


def nom_utile(nom: str) -> bool:
    """
    Filtre les noms d'entités trop pauvres pour être utiles dans un graphe :
    au moins trois lettres, un mot d'au moins trois lettres (« Γ X Y M » et « β/b 1 » sont écartés),
    et pas une phrase entière.
    """
    nom = " ".join(nom.split())
    if not nom or len(nom) > LONGUEUR_NOM_MAXIMUM:
        return False
    lettres = [c for c in nom if c.isalpha()]
    if len(lettres) < 3:
        return False
    return any(sum(c.isalpha() for c in mot) >= 3 for mot in nom.split())


def verifier(entite: dict, passage: str) -> str:
    """Statut d'une proposition, décidé sans le LLM."""
    nom, phrase = normaliser(entite.get("nom", "")), normaliser(entite.get("phrase", ""))
    if not nom or not phrase:
        return REJECTED
    passage_n = normaliser(passage)
    if phrase in passage_n:
        return VERIFIED if nom in phrase else NEEDS_REVIEW
    mots_phrase = set(phrase.split())
    mots_passage = set(passage_n.split())
    couverture = len(mots_phrase & mots_passage) / len(mots_phrase) if mots_phrase else 0.0
    if couverture >= SEUIL_PROCHE and nom in passage_n:
        return NEEDS_REVIEW
    return REJECTED


def extraire_passage(texte: str, appels: list | None = None) -> list[dict]:
    """Entités proposées par le LLM pour un passage (sans contrôle : c'est verifier qui décide)."""
    reponse = llm.chat(
        [{"role": "system", "content": SYSTEME}, {"role": "user", "content": f"Passage :\n{texte}"}],
        SCHEMA, appels=appels, etape="extraction",
    )
    return [e for e in reponse.get("entites", []) if e.get("type") in TYPES]


def selectionner(passages: list[dict]) -> list[dict]:
    """Passages utiles : on écarte les références bibliographiques et les passages trop courts."""
    utiles = [p for p in passages
              if len(p["text"].split()) >= MOTS_MINIMUM and not est_bibliographie(p["text"])]
    return utiles[:PASSAGES_MAXIMUM]


_ACRONYME_ENTRE_PARENTHESES = re.compile(r"\(([A-Z][A-Za-z0-9\-]{1,9})\)\s*$")
_ACRONYME_SEUL = re.compile(r"[A-Z][A-Z0-9\-]{1,9}")


def forme_canonique(nom: str, alias: dict[str, str]) -> str:
    """
    Clé de regroupement d'un nom. Un acronyme et sa forme complète donnent la même clé :
      « quantum anomalous Hall effect (QAHE) » → « qahe », « QAHE » → « qahe ».
    `alias` mémorise les formes complètes déjà vues dans le document, pour les rattacher ensuite à leur acronyme.
    """
    nom = " ".join(nom.split())
    m = _ACRONYME_ENTRE_PARENTHESES.search(nom)
    if m:
        acronyme = normaliser(m.group(1))
        forme_complete = normaliser(nom[:m.start()])
        if forme_complete:
            alias[forme_complete] = acronyme
        return acronyme
    if _ACRONYME_SEUL.fullmatch(nom):
        return normaliser(nom)
    cle = normaliser(nom)
    return alias.get(cle, cle)


def enregistrer(db: Session, user_id: str, document_key: str, titre: str, passage: dict, entite: dict,
                statut: str, alias: dict[str, str] | None = None) -> bool:
    """Ajoute une proposition si elle n'existe pas déjà. Renvoie True si elle est nouvelle."""
    nom_normal = forme_canonique(entite["nom"], alias if alias is not None else {})
    existe = db.scalar(select(KnowledgeProposal.id).where(
        KnowledgeProposal.user_id == user_id,
        KnowledgeProposal.document_key == document_key,
        KnowledgeProposal.entity_type == entite["type"],
        KnowledgeProposal.normalized_name == nom_normal,
        KnowledgeProposal.location == passage.get("location", ""),
    ))
    if existe:
        return False
    db.add(KnowledgeProposal(
        user_id=user_id, document_key=document_key, document_title=titre[:300],
        entity_type=entite["type"], name=entite["nom"].strip()[:300], normalized_name=nom_normal[:300],
        excerpt=" ".join(entite["phrase"].split()), location=passage.get("location", "")[:40],
        verification_status=statut, status="pending",
    ))
    # La session n'a pas d'autoflush : on écrit tout de suite, pour que la prochaine vérification de
    # doublon voie cette proposition (même entité citée deux fois dans un passage).
    db.flush()
    return True


def extraire_document(db: Session, user_id: str, document_key: str, titre: str, passages: list[dict],
                      progres=None, appels: list | None = None) -> dict:
    """
    Extrait, vérifie et enregistre les propositions d'un document.
    `passages` : [{"text": ..., "location": "p. 3"}]. `progres(fait, total)` est appelé à chaque passage.
    Une erreur sur un passage est journalisée, et l'extraction continue avec les suivants.
    """
    selection = selectionner(passages)
    compteurs = {"passages_lus": len(selection), "proposees": 0, "a_relire": 0, "rejetees": 0, "doublons": 0}
    alias: dict[str, str] = {}   # formes complètes → acronymes, partagées par tout le document
    for fait, passage in enumerate(selection):
        if progres:
            progres(fait, len(selection))
        try:
            entites = extraire_passage(passage["text"], appels)
        except llm.OllamaIndisponible:
            raise
        except Exception:  # noqa: BLE001 : un passage mal traité ne doit pas arrêter le document
            logger.exception("Extraction ignorée pour un passage de %s", document_key)
            continue
        for entite in entites:
            statut = verifier(entite, passage["text"])
            if statut == REJECTED or not nom_utile(entite.get("nom", "")):
                compteurs["rejetees"] += 1
                continue
            if enregistrer(db, user_id, document_key, titre, passage, entite, statut, alias):
                compteurs["proposees"] += 1
                compteurs["a_relire"] += statut == NEEDS_REVIEW
            else:
                compteurs["doublons"] += 1
        db.commit()
    if progres:
        progres(len(selection), len(selection))
    return compteurs
