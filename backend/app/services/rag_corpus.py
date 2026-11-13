"""
Pont vers le module `rag/` (recherche hybride + réponse LLM sur le corpus arXiv et les vidéos
de démonstration), construit par la session sœur sur `data_latex/` + `rag/`. Contrat documenté
dans `docs/contrat_api.md` à la racine du dépôt.

`rag/` est un module indépendant (pas un package pip, pas de schémas Pydantic) : on l'importe
en ajoutant la racine du dépôt à sys.path, comme `rag/rag.py` le fait déjà pour trouver son
propre module frère `recherche`. `rag/data/chunks.jsonl` est régénérable mais volumineux et
ignoré par git (voir rag/.gitignore) : disponible() ne renvoie True que s'il existe vraiment
sur cette machine, ce qui laisse `app.services.papers` basculer sur les réponses simulées
ailleurs (dépôt frais, CI) sans rien casser.

ATTENTION : search()/answer() de rag/rag.py n'acceptent aucun filtre par document -- ils
interrogent tout le corpus. Le premier appel construit l'index (BM25 + embeddings E5) :
environ 13 minutes sur CPU pour 3867 chunks (139 articles), sans mise en cache disque
(voir docs/contrat_api.md). answer() appelle Ollama (qwen2.5:3b) en local.
"""
import importlib.util
import sys
from pathlib import Path
from urllib.parse import quote

# backend/app/services/rag_corpus.py -> racine du dépôt (ou du worktree)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEPENDANCES = ("rank_bm25", "sentence_transformers", "numpy")


class RagIndisponible(Exception):
    """rag/ absent, dépendances manquantes, ou Ollama injoignable (voir cause chaînée)."""


def dependances_manquantes() -> list[str]:
    return [d for d in DEPENDANCES if importlib.util.find_spec(d) is None]


def disponible() -> bool:
    """True si le code ET les données du corpus sont présents sur cette machine."""
    return (REPO_ROOT / "rag" / "rag.py").exists() and (REPO_ROOT / "rag" / "data" / "chunks.jsonl").exists()


def _rag():
    manquantes = dependances_manquantes()
    if manquantes:
        raise RagIndisponible(f"rag/ module not installed (missing: {', '.join(manquantes)}).")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import rag.rag as module
    return module


def _label(source: str, document_id: str) -> str:
    return f"arXiv:{document_id}" if source == "article" else document_id


def _lien_article(c: dict) -> str | None:
    """Chemin de la page de l'article dans l'app (frontend /papers/[id]), passage cité inclus."""
    if c["source"] != "article":
        return None
    return f"/papers/{quote(c['document_id'])}?chunk={quote(c['chunk_id'])}"


def search(query: str, top_k: int = 5) -> list[dict]:
    """{chunk_id, document_id, source(label), text, score, timestamp?} -- voir SearchResult."""
    try:
        resultats = _rag().search(query, top_k)
    except RagIndisponible:
        raise
    except Exception as e:  # noqa: BLE001 : erreur de chargement de l'index (fichier corrompu, etc.)
        raise RagIndisponible(f"RAG corpus unavailable: {e}") from e
    return [{"chunk_id": r["chunk_id"], "document_id": r["document_id"],
            "source": _label(r["source"], r["document_id"]), "text": r["text"],
            "score": r["score"], "timestamp": r.get("timestamp")}
            for r in resultats]


def answer(query: str, top_k: int = 5) -> dict:
    """{reponse, citations[{chunk_id,document_id,source,text,timestamp?,url}], verifie}."""
    try:
        rag_module = _rag()
        r = rag_module.answer(query, top_k)
        # Le contrat ne renvoie pas le texte des citations : on le retrouve via un nouveau
        # search() (index déjà chargé en mémoire après le premier appel, donc rapide).
        passages = {p["chunk_id"]: p for p in rag_module.search(query, max(top_k, 5))}
    except RagIndisponible:
        raise
    except Exception as e:  # noqa: BLE001 : Ollama injoignable, index corrompu, etc.
        raise RagIndisponible(f"RAG corpus unavailable: {e}") from e

    citations = []
    for c in r["citations"]:
        p = passages.get(c["chunk_id"], {})
        citations.append({"chunk_id": c["chunk_id"], "document_id": c["document_id"],
                          "source": _label(c["source"], c["document_id"]),
                          "text": p.get("text", ""), "timestamp": p.get("timestamp"),
                          "url": _lien_article(c)})
    return {"reponse": r["reponse"], "citations": citations, "verifie": r["verifie"]}
