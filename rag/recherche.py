"""Recherche hybride commune aux articles et aux videos.

Pipeline : BM25 + E5 -> fusion RRF (top_k de chaque liste) -> candidats -> reranker.
Reproduit le systeme « BM25 + mE5-base » retenu au notebook 10 du depot d'experimentation
(ResearchMind1/ResearchMind-AI) : meme tokenisation BM25, meme formule, meme encodeur, meme
fusion. Les parametres viennent de config_recherche.json ; parite.py verifie sur SciFact que ce
module retrouve les resultats du notebook.

Les embeddings des passages sont mis en cache sur disque (data/cache/), cle = modele + parametres
+ textes : un redemarrage ne les recalcule pas tant que le corpus et la configuration ne changent pas.
"""
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import torch
from nltk.stem.snowball import SnowballStemmer
from sentence_transformers import CrossEncoder, SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

DOSSIER = Path(__file__).resolve().parent
CONFIG = json.loads((DOSSIER / "config_recherche.json").read_text(encoding="utf-8"))
CACHE_EMBEDDINGS = DOSSIER / "data" / "cache"

N_CANDIDATS = CONFIG["reranker"]["candidats"]   # candidats envoyes au reranker
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Mots vides de normaliser(), utilise par la verification lexicale de rag.py (pas par BM25).
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


# ---------- BM25 (notebook 07, repris au notebook 10 cellule 4) ----------

_stem, _stem_cache = SnowballStemmer("english"), {}


def tokeniser(texte):
    toks = [t for t in re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", texte.lower())
            if t not in ENGLISH_STOP_WORDS and len(t) > 1]
    return [_stem_cache.setdefault(t, _stem.stem(t)) for t in toks]


class BM25:
    def __init__(self, textes, k1=CONFIG["bm25"]["k1"], b=CONFIG["bm25"]["b"]):
        cv = CountVectorizer(tokenizer=tokeniser, lowercase=False, token_pattern=None, dtype=np.float32)
        tf = cv.fit_transform(textes).tocoo()
        dl = np.asarray(tf.tocsr().sum(axis=1)).ravel()
        df = np.bincount(tf.col, minlength=tf.shape[1])
        idf = np.log(1 + (len(textes) - df + 0.5) / (df + 0.5)).astype(np.float32)
        w = idf[tf.col] * tf.data * (k1 + 1) / (tf.data + k1 * (1 - b + b * dl[tf.row] / dl.mean()))
        self.W = sp.csc_matrix((w, (tf.row, tf.col)), shape=tf.shape)
        self.vocab = cv.vocabulary_

    def scores(self, question):
        """Scores de tous les passages, ou None si aucun mot de la question n'est dans le vocabulaire."""
        cols = [self.vocab[t] for t in tokeniser(question) if t in self.vocab]
        return np.asarray(self.W[:, cols].sum(axis=1)).ravel() if cols else None


def top_k(scores, k):
    """Les k meilleurs indices, comme le notebook (argpartition puis tri des k)."""
    top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
    return [int(i) for i in top[np.argsort(-scores[top])]]


# ---------- Encodeur E5 (notebook 10 cellule 6) ----------

class Encodeur:
    def __init__(self, cfg=CONFIG["embedding"]):
        self.cfg = cfg
        self.m = SentenceTransformer(cfg["modele"], device=DEVICE)
        self.m.max_seq_length = cfg["max_seq_length"]
        self.fp16 = DEVICE == "cuda" and cfg["fp16_sur_gpu"]
        if self.fp16:
            self.m.half()

    def _enc(self, textes, batch_size=64):
        return self.m.encode(textes, batch_size=batch_size, normalize_embeddings=True,
                             convert_to_numpy=True, show_progress_bar=False).astype(np.float16)

    def passages(self, paires):
        """paires = [(titre, texte)] : « titre. texte » si un titre est donne, comme le notebook."""
        return self._enc([self.cfg["prefixe_passage"] + (t + ". " + x if t else x) for t, x in paires])

    def questions(self, textes):
        return self._enc([self.cfg["prefixe_question"] + t for t in textes])

    def cle_cache(self, paires):
        h = hashlib.sha256(json.dumps([self.cfg, self.fp16], sort_keys=True).encode())
        for t, x in paires:
            h.update(t.encode("utf-8") + b"\x00" + x.encode("utf-8") + b"\x01")
        return h.hexdigest()[:24]

    def passages_en_cache(self, paires, log=print):
        chemin = CACHE_EMBEDDINGS / f"emb_{self.cle_cache(paires)}.npy"
        if chemin.exists():
            log(f"Embeddings lus depuis le cache ({chemin.name})")
            return np.load(chemin)
        log(f"Encodage de {len(paires)} passages avec {self.cfg['modele']} ({DEVICE})...")
        E = self.passages(paires)
        CACHE_EMBEDDINGS.mkdir(parents=True, exist_ok=True)
        np.save(chemin, E)
        return E


def rrf(*classements, k=CONFIG["fusion"]["k"], top=CONFIG["fusion"]["top_k"]):
    """Fusion RRF de classements (listes d'indices), formule et ordre identiques au notebook."""
    sc = defaultdict(float)
    for classement in classements:
        for r, d in enumerate(classement):
            sc[d] += 1 / (k + r + 1)
    return [d for d, _ in sorted(sc.items(), key=lambda x: -x[1])[:top]], sc


class Index:
    """Index BM25 + E5 d'une liste de chunks (articles et/ou videos), avec reranking."""

    def __init__(self, chunks, log=print):
        if not chunks:
            raise ValueError("Aucun chunk a indexer.")
        self.chunks = chunks
        self.textes = [c["text"] for c in chunks]
        self.ids = [c["chunk_id"] for c in chunks]
        self.top_k = CONFIG["fusion"]["top_k"]

        log(f"Indexation BM25 ({len(chunks)} chunks)...")
        self.bm25 = BM25(self.textes)

        log(f"Chargement de {CONFIG['embedding']['modele']}...")
        self.e5 = Encodeur()
        self.emb = self.e5.passages_en_cache([("", t) for t in self.textes], log=log).astype(np.float32)

        log(f"Chargement du reranker ({CONFIG['reranker']['modele']})...")
        self.reranker = CrossEncoder(CONFIG["reranker"]["modele"], max_length=CONFIG["reranker"]["max_length"])

    def classements(self, question):
        """Scores bruts et classements BM25, E5 et hybride RRF (top_k de chaque liste fusionnes)."""
        s_bm25 = self.bm25.scores(question)
        s_e5 = self.emb @ self.e5.questions([question])[0].astype(np.float32)
        l_bm25 = top_k(s_bm25, self.top_k) if s_bm25 is not None else []
        l_e5 = top_k(s_e5, self.top_k)
        l_rrf, sc_rrf = rrf(l_bm25, l_e5)
        return {"bm25": s_bm25 if s_bm25 is not None else np.zeros(len(self.chunks)), "e5": s_e5,
                "rrf": sc_rrf, "BM25": l_bm25, "E5": l_e5, "Hybride RRF": l_rrf}

    def rerank(self, question, candidats):
        """Probabilites du reranker pour (question, passage) sur les indices candidats."""
        return probas(self.reranker.predict([(question, self.textes[i]) for i in candidats],
                                            show_progress_bar=False))

    def rechercher(self, question, n=N_CANDIDATS):
        """Les n premiers candidats RRF reclasses par le reranker, avec scores et rangs."""
        c = self.classements(question)
        r_bm25 = {i: r for r, i in enumerate(c["BM25"], start=1)}
        r_e5 = {i: r for r, i in enumerate(c["E5"], start=1)}
        candidats = c["Hybride RRF"][:n]
        sc = self.rerank(question, candidats)
        resultats = [{"idx": i, "chunk": self.chunks[i],
                      "bm25": float(c["bm25"][i]), "rang_bm25": r_bm25.get(i),
                      "e5": float(c["e5"][i]), "rang_e5": r_e5.get(i),
                      "rrf": float(c["rrf"][i]), "rang_rrf": k,
                      "rerank": float(s)}
                     for k, (i, s) in enumerate(zip(candidats, sc), start=1)]
        resultats.sort(key=lambda x: x["rerank"], reverse=True)
        return resultats
