"""Découpage d'une transcription en chunks avec provenance (repris de decouper.py)."""
import hashlib

from .config import CHEVAUCHEMENT, MAX_MOTS, MAX_SECONDES
from .text import hms


def decouper(segments: list[dict], max_secondes: float = MAX_SECONDES,
             max_mots: int = MAX_MOTS, chevauchement: int = CHEVAUCHEMENT) -> list[list[dict]]:
    """Regroupe les segments consécutifs jusqu'à max_secondes ou max_mots."""
    groupes, courant = [], []
    for seg in segments:
        if courant:
            duree = seg["end"] - courant[0]["start"]
            mots = sum(len(s["text"].split()) for s in courant) + len(seg["text"].split())
            if duree > max_secondes or mots > max_mots:
                groupes.append(courant)
                courant = courant[-chevauchement:] if chevauchement else []
        courant.append(seg)
    if courant:
        groupes.append(courant)
    return groupes


def document_id(source: str) -> str:
    """Identifiant stable d'une vidéo, dérivé de son URL ou de son nom de fichier."""
    return "video_" + hashlib.md5(source.encode()).hexdigest()[:10]


def construire_chunks(segments: list[dict], source: str, titre: str,
                      langue: str | None = None, doc_id: str | None = None) -> list[dict]:
    """Chunks prêts à indexer : texte, début/fin en secondes, horodatage lisible."""
    doc_id = doc_id or document_id(source)
    chunks = []
    for i, groupe in enumerate(decouper(segments)):
        debut, fin = groupe[0]["start"], groupe[-1]["end"]
        chunks.append({
            "chunk_id": f"{doc_id}_{i:04d}",
            "document_id": doc_id,
            "source_type": "video",
            "source": source,
            "title": titre,
            "language": langue,
            "start": round(debut, 2),
            "end": round(fin, 2),
            "timestamp": f"{hms(debut)} - {hms(fin)}",
            "text": " ".join(s["text"] for s in groupe),
        })
    return chunks
