"""
Recherche hybride (reprise de recherche.py) : BM25 + E5 -> fusion RRF -> N_CANDIDATS -> cross-encodeur.

Seul le reranker MiniLM est conservé. Les modèles E5 et cross-encodeur sont chargés une
fois par processus et partagés entre les index (un index par vidéo).
"""
from functools import lru_cache

from .config import MODELE_E5, MODELE_RERANKER, N_CANDIDATS, RRF_K
from .text import normaliser


def ordre(scores):
    """Indices triés par score décroissant (tri stable : à égalité, ordre des chunks)."""
    import numpy as np

    return [int(i) for i in np.argsort(-np.asarray(scores, dtype=float), kind="stable")]


def probas(scores):
    """Logits bruts -> probabilités ; laisse intacts des scores déjà dans [0, 1]."""
    import numpy as np

    s = np.asarray(scores, dtype=float)
    return 1 / (1 + np.exp(-s)) if (s.min() < 0 or s.max() > 1) else s


def rrf(listes_scores, n):
    """Fusion RRF de plusieurs listes de scores portant sur les mêmes n chunks."""
    import numpy as np

    fusion = np.zeros(n)
    for s in listes_scores:
        for r, i in enumerate(ordre(s), start=1):
            fusion[i] += 1 / (RRF_K + r)
    return fusion


@lru_cache(maxsize=1)
def modele_e5():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELE_E5)


@lru_cache(maxsize=1)
def modele_reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(MODELE_RERANKER, max_length=512)


class Index:
    """Index BM25 + E5 des chunks d'une vidéo, avec reranking par cross-encodeur."""

    def __init__(self, chunks: list[dict], embeddings=None):
        """embeddings : vecteurs E5 déjà calculés (passage), pour éviter de les recalculer."""
        import numpy as np
        from rank_bm25 import BM25Okapi

        if not chunks:
            raise ValueError("Aucun chunk à indexer.")
        self.chunks = chunks
        self.textes = [c["text"] for c in chunks]
        self.bm25 = BM25Okapi([normaliser(t) for t in self.textes])
        self.e5 = modele_e5()
        self.emb = np.asarray(embeddings if embeddings is not None else encoder_passages(self.textes))
        self.reranker = modele_reranker()

    def classements(self, question: str) -> dict:
        """Scores bruts et classements BM25, E5 et hybride RRF."""
        n = len(self.chunks)
        s_bm25 = self.bm25.get_scores(normaliser(question))
        s_e5 = self.emb @ self.e5.encode("query: " + question, normalize_embeddings=True)
        fusion = rrf([s_bm25, s_e5], n)
        return {"bm25": s_bm25, "e5": s_e5, "rrf": fusion,
                "BM25": ordre(s_bm25), "E5": ordre(s_e5), "Hybride RRF": ordre(fusion)}

    def scorer(self, question: str, textes: list[str]):
        """Probabilités du cross-encodeur pour (question, texte)."""
        return probas(self.reranker.predict([(question, t) for t in textes],
                                            show_progress_bar=False))

    def rechercher(self, question: str, n: int = N_CANDIDATS) -> list[dict]:
        """Les n candidats RRF reclassés par le cross-encodeur, avec scores et rangs."""
        c = self.classements(question)
        r_bm25 = {i: r for r, i in enumerate(c["BM25"], start=1)}
        r_e5 = {i: r for r, i in enumerate(c["E5"], start=1)}
        candidats = c["Hybride RRF"][:n]
        sc = self.scorer(question, [self.textes[i] for i in candidats])
        resultats = [{"idx": i, "chunk": self.chunks[i],
                      "bm25": float(c["bm25"][i]), "rang_bm25": r_bm25[i],
                      "e5": float(c["e5"][i]), "rang_e5": r_e5[i],
                      "rrf": float(c["rrf"][i]), "rang_rrf": k,
                      "rerank": float(s)}
                     for k, (i, s) in enumerate(zip(candidats, sc), start=1)]
        resultats.sort(key=lambda x: x["rerank"], reverse=True)
        return resultats


def encoder_passages(textes: list[str]):
    """Vecteurs E5 normalisés des passages (à stocker avec les chunks si besoin)."""
    return modele_e5().encode(["passage: " + t for t in textes],
                              normalize_embeddings=True, show_progress_bar=False)
