"""Recherche hybride commune aux articles et aux videos (porte de D:\\Transcription\\recherche.py).

Pipeline : BM25 + E5 -> fusion RRF -> N_CANDIDATS candidats -> reranker MiniLM.
Le tri est toujours stable (np.argsort kind="stable") : a egalite de score, l'ordre
d'origine des chunks est conserve, pour des resultats reproductibles.
"""
import re
import unicodedata

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

MODELE_E5 = "intfloat/multilingual-e5-small"
MODELE_RERANKER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
N_CANDIDATS = 10   # candidats envoyes au reranker
RRF_K = 60

MOTS_VIDES = set("""le la les un une des de du d l et ou en au aux a à ce ces cet cette
qui que quoi dont où il elle ils elles on je tu nous vous se sa son ses leur leurs
est sont été être avoir pas ne n y ça c s qu pour par sur dans avec plus mais
the a an of to and or in on is are was it that this for with as be""".split())


def normaliser(texte):
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return [m for m in re.findall(r"\w+", texte) if m not in MOTS_VIDES and len(m) > 1]


def ordre(scores):
    """Indices tries par score decroissant (tri stable : a egalite, ordre des chunks)."""
    return [int(i) for i in np.argsort(-np.asarray(scores, dtype=float), kind="stable")]


def probas(scores):
    """Logits bruts -> probabilites ; laisse intacts des scores deja dans [0, 1]."""
    s = np.asarray(scores, dtype=float)
    return 1 / (1 + np.exp(-s)) if (s.min() < 0 or s.max() > 1) else s


def rrf(listes_scores, n):
    """Fusion RRF de plusieurs listes de scores portant sur les memes n chunks."""
    fusion = np.zeros(n)
    for s in listes_scores:
        for r, i in enumerate(ordre(s), start=1):
            fusion[i] += 1 / (RRF_K + r)
    return fusion


class Index:
    """Index BM25 + E5 d'une liste de chunks (articles et/ou videos), avec reranking MiniLM."""

    def __init__(self, chunks, log=print):
        if not chunks:
            raise ValueError("Aucun chunk a indexer.")
        self.chunks = chunks
        self.textes = [c["text"] for c in chunks]
        self.ids = [c["chunk_id"] for c in chunks]

        log(f"Indexation BM25 ({len(chunks)} chunks)...")
        self.bm25 = BM25Okapi([normaliser(t) for t in self.textes])

        log(f"Chargement de {MODELE_E5}...")
        self.e5 = SentenceTransformer(MODELE_E5)
        self.emb = self.e5.encode(["passage: " + t for t in self.textes],
                                  normalize_embeddings=True, show_progress_bar=False)

        log(f"Chargement du reranker ({MODELE_RERANKER})...")
        self.reranker = CrossEncoder(MODELE_RERANKER, max_length=512)

    def classements(self, question):
        """Scores bruts et classements BM25, E5 et hybride RRF."""
        n = len(self.chunks)
        s_bm25 = self.bm25.get_scores(normaliser(question))
        s_e5 = self.emb @ self.e5.encode("query: " + question, normalize_embeddings=True)
        fusion = rrf([s_bm25, s_e5], n)
        return {"bm25": s_bm25, "e5": s_e5, "rrf": fusion,
                "BM25": ordre(s_bm25), "E5": ordre(s_e5), "Hybride RRF": ordre(fusion)}

    def rerank(self, question, candidats):
        """Probabilites du reranker pour (question, passage) sur les indices candidats."""
        return probas(self.reranker.predict([(question, self.textes[i]) for i in candidats],
                                            show_progress_bar=False))

    def rechercher(self, question, n=N_CANDIDATS):
        """Les n candidats RRF reclasses par le reranker, avec scores et rangs (tri stable)."""
        c = self.classements(question)
        r_bm25 = {i: r for r, i in enumerate(c["BM25"], start=1)}
        r_e5 = {i: r for r, i in enumerate(c["E5"], start=1)}
        candidats = c["Hybride RRF"][:n]
        sc = self.rerank(question, candidats)
        resultats = [{"idx": i, "chunk": self.chunks[i],
                      "bm25": float(c["bm25"][i]), "rang_bm25": r_bm25[i],
                      "e5": float(c["e5"][i]), "rang_e5": r_e5[i],
                      "rrf": float(c["rrf"][i]), "rang_rrf": k,
                      "rerank": float(s)}
                     for k, (i, s) in enumerate(zip(candidats, sc), start=1)]
        resultats.sort(key=lambda x: x["rerank"], reverse=True)
        return resultats
