"""Chunking unifie articles (.tex) + videos : un schema commun pour l'indexation RAG.

Schema commun (un objet JSON par chunk) :
  chunk_id     : identifiant unique du chunk
  document_id  : identifiant du document source (id arXiv pour un article, id video pour une video)
  source       : "article" ou "video"
  section      : titre de section (article) ou titre de la video (video)
  text         : texte du chunk
  + pour les videos uniquement : start, end, timestamp (secondes / "hh:mm:ss - hh:mm:ss")

Les articles sont decoupes a partir des sources .tex via data_latex/scripts/chunk_embed.py,
reutilise ici tel quel (pas de duplication de la logique d'extraction LaTeX). Les videos sont
deja decoupees par backend/app/services/video/chunking.py (ou son prototype
D:\\Transcription\\decouper.py) ; backend/ n'est pas modifie dans cette mission (une autre
session y travaille), donc ce module se contente de relire leur JSON de sortie et de le
remettre au format commun ci-dessus.

Usage :
  python -I chunking.py --out data/chunks.jsonl
  python -I chunking.py --out data/chunks.jsonl --video-json chemin/video1_chunks.json ...
"""
import argparse
import json
import sys
from pathlib import Path

_DATA_LATEX_SCRIPTS = Path(__file__).resolve().parents[1] / "data_latex" / "scripts"
sys.path.insert(0, str(_DATA_LATEX_SCRIPTS))
from chunk_embed import DOMAINS, chunks_article, lister_articles  # noqa: E402


def chunks_articles(data_dir, domaines=None, ids=None, limit=None):
    """Chunks de tous les articles de data_latex/data, au format commun ci-dessus."""
    domaines = domaines or list(DOMAINS)
    ids = set(ids) if ids else None
    resultats = []
    for dom, doc_id, tex_dir in lister_articles(Path(data_dir), domaines, ids, limit):
        for c in chunks_article(dom, doc_id, tex_dir):
            resultats.append({
                "chunk_id": c["chunk_id"],
                "document_id": c["doc_id"],
                "source": "article",
                "section": c["section_title"],
                "text": c["text"],
            })
    return resultats


def chunks_video(chemin_json):
    """Relit un fichier de chunks video deja decoupe (decouper.py / chunking.py backend) et
    le remet au format commun. Le champ "source" d'origine du fichier video (url/fichier)
    est garde sous "origine" pour ne pas entrer en conflit avec notre "source" = type de document.
    """
    with open(chemin_json, encoding="utf-8") as f:
        data = json.load(f)
    brut = data["chunks"] if isinstance(data, dict) and "chunks" in data else data
    return [{
        "chunk_id": c["chunk_id"],
        "document_id": c["document_id"],
        "source": "video",
        "section": c.get("title") or "",
        "text": c["text"],
        "start": c.get("start"),
        "end": c.get("end"),
        "timestamp": c.get("timestamp"),
        "origine": c.get("source"),
    } for c in brut]


def ecrire_chunks(chunks, chemin):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-latex", default=str(Path(__file__).resolve().parents[1] / "data_latex" / "data"))
    p.add_argument("--video-json", nargs="*", default=[], help="fichiers de chunks video a inclure")
    p.add_argument("--out", default=str(Path(__file__).resolve().parent / "data" / "chunks.jsonl"))
    args = p.parse_args()

    chunks = chunks_articles(args.data_latex)
    for vj in args.video_json:
        chunks += chunks_video(vj)
    ecrire_chunks(chunks, args.out)

    n_art = sum(c["source"] == "article" for c in chunks)
    n_vid = sum(c["source"] == "video" for c in chunks)
    print(f"{len(chunks)} chunks ({n_art} article, {n_vid} video) -> {args.out}")


if __name__ == "__main__":
    main()
