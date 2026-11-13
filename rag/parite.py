"""Test de parite : le module recherche.py reproduit-il le systeme evalue au notebook 10 ?

Rejoue SciFact (split test) avec recherche.py et compare a trois niveaux aux sorties du notebook,
lues dans le depot d'experimentation (jamais recopiees a la main) :
  1. embeddings des documents   vs models/emb/scifact__mE5-base.npy        (cosinus)
  2. classement BM25 (top 10)   vs results/runs/scifact__BM25_classique.trec (identite)
  3. nDCG@10 BM25, mE5-base, BM25 + mE5-base vs results/metrics.csv (notebook 10)

Sortie : results/parite.csv. Code de retour 1 si une verification echoue.

Usage :
  python -I parite.py [--experiences CHEMIN_VERS_ResearchMind-AI]
"""
import argparse
import csv
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER))
import numpy as np  # noqa: E402

from recherche import BM25, CONFIG, Encodeur, rrf, top_k  # noqa: E402

DATASET, SPLIT = "scifact", "test"
TOLERANCE_NDCG = 0.005        # ecart absolu admis (fp16, materiel different)
COSINUS_MIN = 0.999           # cosinus moyen minimal entre nos embeddings et ceux du notebook
IDENTITE_BM25_MIN = 0.99      # part minimale de questions au top 10 BM25 identique


def charger(exp):
    corpus = {}
    with open(exp / "data/processed/passages" / f"{DATASET}.jsonl", encoding="utf-8") as f:
        for ligne in f:
            u = json.loads(ligne)
            corpus[u["unit_id"]] = (u.get("title") or "", u.get("text") or "")
    questions = {}
    with open(exp / "data/processed/metadata" / f"{DATASET}_queries.jsonl", encoding="utf-8") as f:
        for ligne in f:
            q = json.loads(ligne)
            questions[q["qid"]] = q["text"]
    qrels = defaultdict(dict)
    for ligne in open(exp / "data/qrels" / f"{DATASET}_{SPLIT}.tsv", encoding="utf-8"):
        qid, _, uid, g = ligne.rstrip("\n").split("\t")
        if uid in corpus:
            qrels[qid][uid] = int(g)
    return corpus, questions, dict(qrels)


def ndcg10(run, qrels):
    """Meme formule que per_query() du notebook 10 (cellule 3)."""
    vals = []
    for qid, rel in qrels.items():
        top = run.get(qid, [])[:10]
        dcg = sum(rel.get(d, 0) / math.log2(i + 2) for i, d in enumerate(top))
        idcg = sum(g / math.log2(i + 2) for i, g in enumerate(sorted(rel.values(), reverse=True)[:10]))
        vals.append(dcg / idcg if idcg else 0.0)
    return round(float(np.mean(vals)), 4)


def references(exp):
    """Derniere valeur de nDCG@10 du notebook 10 pour chaque systeme, sur SciFact test."""
    ref = {}
    with open(exp / "results/metrics.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["notebook"] == "10" and row["dataset"] == DATASET and row["split"] == SPLIT:
                ref[row["système"]] = float(row["nDCG@10"])
    return ref


def lire_trec(chemin):
    run = defaultdict(list)
    for ligne in open(chemin, encoding="utf-8"):
        qid, _, uid, *_ = ligne.split()
        run[qid].append(uid)
    return dict(run)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--experiences", type=Path, default=DOSSIER.parents[1] / "ResearchMind1" / "ResearchMind-AI")
    args = p.parse_args()
    exp = args.experiences
    t0 = time.perf_counter()

    corpus, questions, qrels = charger(exp)
    ids = list(corpus)
    qtest = {q: questions[q] for q in qrels}
    print(f"{DATASET} {SPLIT} : {len(corpus)} documents, {len(qtest)} questions")
    ref = references(exp)
    nom_e5 = "mE5-base"
    if CONFIG["embedding"]["modele"] != "intfloat/multilingual-e5-base":
        print(f"Attention : la configuration utilise {CONFIG['embedding']['modele']}, la reference est {nom_e5}.")

    verifs = []

    def verifier(nom, valeur, attendu, ok, detail=""):
        verifs.append({"verification": nom, "valeur": valeur, "attendu": attendu, "ok": ok, "detail": detail})
        print(f"  [{'OK ' if ok else 'ECHEC'}] {nom} : {valeur} (attendu {attendu}) {detail}")

    # BM25
    bm25 = BM25([(t + " " + x).strip() for t, x in corpus.values()])
    run_bm25 = {}
    for qid, texte in qtest.items():
        s = bm25.scores(texte)
        run_bm25[qid] = [ids[i] for i in top_k(s, CONFIG["fusion"]["top_k"])] if s is not None else []
    trec = exp / "results/runs" / f"{DATASET}__BM25_classique.trec"
    if trec.exists():
        ref_run = lire_trec(trec)
        communs = [q for q in qtest if q in ref_run]
        identiques = sum(run_bm25[q][:10] == ref_run[q][:10] for q in communs) / max(len(communs), 1)
        verifier("BM25 top 10 identique au run du notebook", round(identiques, 4), f">= {IDENTITE_BM25_MIN}",
                 identiques >= IDENTITE_BM25_MIN, f"({len(communs)} questions)")
    n_bm25 = ndcg10(run_bm25, qrels)
    verifier("nDCG@10 BM25", n_bm25, ref.get("BM25"), ref.get("BM25") is not None and abs(n_bm25 - ref["BM25"]) <= TOLERANCE_NDCG)

    # Encodeur
    enc = Encodeur()
    E = enc.passages_en_cache(list(corpus.values())).astype(np.float32)
    emb_nb = exp / "models/emb" / f"{DATASET}__{nom_e5}.npy"
    if emb_nb.exists():
        R = np.load(emb_nb).astype(np.float32)
        if R.shape == E.shape:
            cos = (E * R).sum(1) / (np.linalg.norm(E, axis=1) * np.linalg.norm(R, axis=1))
            verifier("Cosinus moyen embeddings vs notebook", round(float(cos.mean()), 5), f">= {COSINUS_MIN}",
                     float(cos.mean()) >= COSINUS_MIN, f"(minimum {cos.min():.5f})")
        else:
            verifier("Forme des embeddings", str(E.shape), str(R.shape), False)

    qids = list(qtest)
    Q = enc.questions([qtest[q] for q in qids]).astype(np.float32)
    S = Q @ E.T
    run_e5 = {q: [ids[i] for i in top_k(S[j], CONFIG["fusion"]["top_k"])] for j, q in enumerate(qids)}
    n_e5 = ndcg10(run_e5, qrels)
    verifier(f"nDCG@10 {nom_e5}", n_e5, ref.get(nom_e5),
             ref.get(nom_e5) is not None and abs(n_e5 - ref[nom_e5]) <= TOLERANCE_NDCG)

    run_hyb = {q: rrf(run_bm25[q], run_e5[q])[0] for q in qids}
    n_hyb = ndcg10(run_hyb, qrels)
    cle = f"BM25 + {nom_e5}"
    verifier(f"nDCG@10 {cle}", n_hyb, ref.get(cle), ref.get(cle) is not None and abs(n_hyb - ref[cle]) <= TOLERANCE_NDCG)

    sortie = DOSSIER / "results" / "parite.csv"
    sortie.parent.mkdir(exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "dataset", "verification", "valeur", "attendu", "ok", "detail"])
        w.writeheader()
        for v in verifs:
            w.writerow({"date": date, "dataset": f"{DATASET}/{SPLIT}", **v})

    ok = all(v["ok"] for v in verifs)
    print(f"\nParite {'OK' if ok else 'ECHOUEE'} ({time.perf_counter() - t0:.0f} s) -> {sortie}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
