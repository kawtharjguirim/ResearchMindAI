"""
Articles arXiv du corpus data_latex : métadonnées et PDF (data_latex/data/index/documents.jsonl)
et passages découpés par rag/chunking.py (rag/data/chunks.jsonl), reliés par le même doc_id
(= document_id des chunks et des citations).

Les chemins de PDF viennent uniquement de documents.jsonl, jamais de l'URL : un doc_id inconnu
renvoie None.
"""
import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data_latex" / "data"
DOCUMENTS = DATA_DIR / "index" / "documents.jsonl"
CHUNKS = REPO_ROOT / "rag" / "data" / "chunks.jsonl"


def _lire_jsonl(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


@lru_cache(maxsize=1)
def _documents() -> dict[str, dict]:
    return {d["doc_id"]: d for d in _lire_jsonl(DOCUMENTS)}


@lru_cache(maxsize=1)
def _chunks() -> dict[str, dict]:
    return {c["chunk_id"]: c for c in _lire_jsonl(CHUNKS)}


def documents() -> list[dict]:
    return list(_documents().values())


def document(doc_id: str) -> dict | None:
    return _documents().get(doc_id)


def pdf_path(doc_id: str) -> Path | None:
    d = document(doc_id)
    if d is None or not d.get("pdf_path"):
        return None
    chemin = (DATA_DIR / d["pdf_path"]).resolve()
    if not chemin.is_relative_to(DATA_DIR.resolve()) or not chemin.is_file():
        return None
    return chemin


def passage(doc_id: str, chunk_id: str) -> dict | None:
    """Le chunk cité, seulement s'il appartient bien à ce document."""
    c = _chunks().get(chunk_id)
    if c is None or c.get("document_id") != doc_id:
        return None
    return {"chunk_id": c["chunk_id"], "section": c.get("section", ""), "text": c["text"]}
