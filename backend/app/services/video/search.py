"""
Recherche des vidéos : le moteur commun de rag/recherche.py (même modèle d'embedding, même
fusion et même reranker que les articles, voir rag/config_recherche.json), avec un BM25 sur
normaliser(), adapté au français des transcriptions.

Pourquoi ce choix : rag/results/evaluation_video.csv compare l'ancien moteur vidéo et les
variantes du moteur commun sur la même vidéo ; le BM25 du notebook 10 (anglais) dégrade la
recherche vidéo, la variante BM25 français fait jeu égal avec l'ancien moteur.
"""
import sys
from pathlib import Path

_RAG = Path(__file__).resolve().parents[4] / "rag"
if str(_RAG) not in sys.path:
    sys.path.insert(0, str(_RAG))

from recherche import Encodeur  # noqa: E402
from recherche import Index as _IndexCommun  # noqa: E402
from recherche import normaliser  # noqa: E402


class Index(_IndexCommun):
    """Index d'une vidéo. embeddings : vecteurs stockés en base ; recalculés s'ils viennent
    d'un autre modèle (anciennes vidéos encodées avec e5-small)."""

    def __init__(self, chunks: list[dict], embeddings=None):
        super().__init__(chunks, log=lambda *_: None, embeddings=embeddings, tokeniser=normaliser,
                         cache_disque=False)


def encoder_passages(textes: list[str]):
    """Vecteurs des passages avec le modèle configuré, à stocker avec les chunks."""
    return Encodeur().passages([("", t) for t in textes])
