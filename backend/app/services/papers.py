"""
Sources "papier" (PDF, web, figure, document personnel).

Deux modes, choisis à l'appel selon `rag_corpus.disponible()` :
- corpus réel : si `rag/` (code + données, voir app.services.rag_corpus) est présent sur cette
  machine, une seule source pseudo-document CORPUS_ID représente tout le corpus arXiv indexé
  par la session sœur (`search()`/`answer()` de rag/rag.py interrogent le corpus entier, sans
  filtre par document : voir docs/contrat_api.md).
- simulé : sinon (dépôt frais, CI, données non générées localement), un petit jeu de données
  statique pour que GET /sources, POST /search et POST /answer aient de quoi afficher/chercher/
  répondre sur des sources non-vidéo.
"""
from datetime import datetime, timezone
from pathlib import Path

from app.services import rag_corpus

# backend/app/services/papers.py -> parents[3] = racine du dépôt (ou du worktree)
CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "contrat_api.md"

CORPUS_ID = "corpus-arxiv"

# Horodatage fixe (déterministe pour les tests et le tri par date de création).
_BASE = datetime(2025, 9, 1, tzinfo=timezone.utc)

MOCK_PAPERS: list[dict] = [
    {
        "id": "paper-demo-relativity",
        "source_type": "pdf",
        "title": "Relativistic corrections in GPS timekeeping",
        "url": "https://arxiv.org/abs/demo-relativity#section-3",
        "excerpt": "Corrections relativistes appliquées aux horloges des satellites GPS.",
        "language": "en",
        "chunks": [
            {"chunk_id": "paper-demo-relativity-c1", "section": "3. Relativistic corrections",
             "text": "The GPS system must account for both special and general relativistic "
                     "effects to maintain timing accuracy across the satellite constellation."},
            {"chunk_id": "paper-demo-relativity-c2", "section": "3.2 Magnitude of the effect",
             "text": "Without correction, onboard satellite clocks would drift by roughly "
                     "38 microseconds per day relative to clocks on the ground."},
        ],
    },
    {
        "id": "paper-demo-rag",
        "source_type": "web",
        "title": "Retrieval-Augmented Generation: a survey",
        "url": "https://example.org/rag-survey#introduction",
        "excerpt": "Panorama des architectures combinant recherche documentaire et génération.",
        "language": "en",
        "chunks": [
            {"chunk_id": "paper-demo-rag-c1", "section": "1. Introduction",
             "text": "Retrieval-augmented generation grounds a language model's answer in "
                     "passages retrieved from an external knowledge source."},
            {"chunk_id": "paper-demo-rag-c2", "section": "2.1 Hybrid retrieval",
             "text": "Combining sparse lexical search such as BM25 with dense embeddings "
                     "typically improves recall over either method alone."},
        ],
    },
    {
        "id": "paper-demo-notes",
        "source_type": "personal",
        "title": "Notes de lecture - architecture RAG",
        "url": "",
        "excerpt": "Notes personnelles prises pendant la revue de littérature.",
        "language": "fr",
        "chunks": [
            {"chunk_id": "paper-demo-notes-c1", "section": "Synthèse",
             "text": "Le reranker apporte le plus gros gain de précision, bien plus que le "
                     "choix du modèle d'embeddings."},
        ],
    },
]

_BY_ID = {p["id"] for p in MOCK_PAPERS}


def is_paper_id(source_id: str) -> bool:
    return source_id in _BY_ID or source_id == CORPUS_ID


def contrat_disponible() -> bool:
    """True si le contrat réel du corpus (docs/contrat_api.md) a été publié."""
    return CONTRACT_PATH.exists()


def get_paper(source_id: str) -> dict | None:
    return next((p for p in MOCK_PAPERS if p["id"] == source_id), None)


def _score(query: str, text: str) -> float:
    """Score simulé déterministe : chevauchement de mots entre la question et le passage."""
    mots_q = {m for m in query.lower().split() if len(m) > 2}
    mots_t = {m for m in text.lower().split() if len(m) > 2}
    if not mots_q or not mots_t:
        return 0.0
    return round(len(mots_q & mots_t) / len(mots_q), 4)


# ---------- Mode simulé (repli) ----------

def _list_sources_simulees() -> list[dict]:
    return [
        {
            "id": p["id"], "project_id": None, "source_type": p["source_type"], "title": p["title"],
            "url": p["url"], "language": p["language"], "duration": None, "status": "ready", "error": "",
            "excerpt": p["excerpt"], "chunk_count": len(p["chunks"]),
            "created_at": _BASE.isoformat(), "updated_at": _BASE.isoformat(),
        }
        for p in MOCK_PAPERS
    ]


def _search_simulee(query: str, source_id: str | None, top_k: int) -> list[dict]:
    papers = [get_paper(source_id)] if source_id else MOCK_PAPERS
    resultats = []
    for p in papers:
        if p is None:
            continue
        for c in p["chunks"]:
            resultats.append({
                "chunk_id": c["chunk_id"], "document_id": p["id"], "source": p["title"],
                "text": c["text"], "score": _score(query, c["text"]), "timestamp": None,
            })
    resultats.sort(key=lambda r: r["score"], reverse=True)
    return resultats[:top_k]


def _answer_simulee(question: str, source_id: str) -> dict:
    p = get_paper(source_id)
    if p is None:
        return {"reponse": "Source papier introuvable.", "citations": [], "verifie": False}
    resultats = _search_simulee(question, source_id, top_k=1)
    if not resultats:
        return {"reponse": "Aucun passage simulé ne correspond à cette question.",
                "citations": [], "verifie": False}
    top = resultats[0]
    citation = {"chunk_id": top["chunk_id"], "document_id": p["id"], "source": p["title"],
                "text": top["text"], "timestamp": None, "url": p["url"] or None}
    reponse = (f"Réponse simulée (corpus papier non encore branché) : « {top['text']} » "
              f"— à vérifier, ce passage est un exemple de démonstration, pas une vraie extraction.")
    return {"reponse": reponse, "citations": [citation], "verifie": False}


# ---------- Mode corpus réel (rag/, voir app.services.rag_corpus) ----------

def _nb_chunks_corpus() -> int:
    chemin = rag_corpus.REPO_ROOT / "rag" / "data" / "chunks.jsonl"
    with open(chemin, encoding="utf-8") as f:
        return sum(1 for _ in f)


def _list_sources_corpus() -> list[dict]:
    return [{
        "id": CORPUS_ID, "project_id": None, "source_type": "pdf", "title": "Corpus arXiv (data_latex)",
        "url": "", "language": "en", "duration": None, "status": "ready", "error": "",
        "excerpt": "Recherche hybride (BM25 + E5 + reranker) sur les articles arXiv importés "
                   "et les vidéos de démonstration. Une question interroge tout le corpus.",
        "chunk_count": _nb_chunks_corpus(),
        "created_at": _BASE.isoformat(), "updated_at": _BASE.isoformat(),
    }]


# ---------- API publique (app.api.routes.sources/answer/search) ----------

def list_sources() -> list[dict]:
    """Sources papier au format attendu par SourceRead (status toujours "ready": pas de traitement)."""
    return _list_sources_corpus() if rag_corpus.disponible() else _list_sources_simulees()


def search(query: str, source_id: str | None = None, top_k: int = 5) -> list[dict]:
    """Résultats au format {chunk_id, document_id, source, text, score, timestamp?}."""
    if rag_corpus.disponible():
        return rag_corpus.search(query, top_k)
    return _search_simulee(query, source_id, top_k)


def answer(question: str, source_id: str) -> dict:
    """{reponse, citations, verifie} : corpus réel si disponible, sinon réponse simulée."""
    if rag_corpus.disponible():
        return rag_corpus.answer(question, top_k=5)
    return _answer_simulee(question, source_id)
