"""Compare des variantes du moteur commun (recherche.py) sur une video et ses questions.

La variante A (ancien moteur video : e5-small, BM25 rank_bm25 sur normaliser()) a ete mesuree le
14/11/2026 avant son remplacement : ses chiffres restent dans results/evaluation_video.csv. La video
utilise depuis la variante C (backend/app/services/video/search.py).

Variantes :
  B  moteur commun tel quel : mE5-base, BM25 du notebook 10 (anglais), RRF top 100
  C  moteur commun, BM25 sur normaliser() (francais)
  D  moteur commun, E5 seul (sans BM25)
Pour chacune : classement avant reranker, puis reranking des N_CANDIDATS premiers par le meme
cross-encodeur. Questions hors sujet : rejetees si le meilleur score du reranker < plancher video.

Usage :
  python -I evaluation_video.py --chunks <..._chunks.json> --questions <q1.json> [<q2.json> ...]
Sortie : results/evaluation_video_commun.csv
"""
import argparse
import csv
import json
import sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER))
import numpy as np  # noqa: E402
from sentence_transformers import CrossEncoder  # noqa: E402

from recherche import BM25, CONFIG, Encodeur, normaliser, probas, rrf, top_k  # noqa: E402

PLANCHER = 0.02       # backend/app/services/video/config.py : PLANCHER_RERANK
N_CAND = 10


def premier_rang(ids_classes, pertinents):
    for r, c in enumerate(ids_classes[:10], start=1):
        if c in pertinents:
            return r
    return None


def resume(rangs):
    n = len(rangs)
    return (sum(1 for r in rangs if r == 1) / n, sum(1 for r in rangs if r and r <= 3) / n,
            sum(1 / r for r in rangs if r) / n)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chunks", required=True)
    p.add_argument("--questions", nargs="+", required=True)
    args = p.parse_args()

    chunks = json.loads(Path(args.chunks).read_text(encoding="utf-8"))
    ids = [c["chunk_id"] for c in chunks]
    textes = [c["text"] for c in chunks]
    jeux = {Path(f).stem: json.loads(Path(f).read_text(encoding="utf-8")) for f in args.questions}
    reranker = CrossEncoder(CONFIG["reranker"]["modele"], max_length=CONFIG["reranker"]["max_length"])

    def reranke(question, candidats):
        sc = probas(reranker.predict([(question, textes[i]) for i in candidats], show_progress_bar=False))
        ordre = [candidats[i] for i in np.argsort(-sc, kind="stable")]
        return ordre, float(sc.max())

    # Variantes du moteur commun : fonctions question -> (liste avant reranker)
    enc = Encodeur()
    E = enc.passages_en_cache([("", t) for t in textes], log=lambda *_: None).astype(np.float32)
    bm_en, bm_fr = BM25(textes), BM25(textes, tokeniser=normaliser)

    def liste_commune(bm):
        def f(q):
            s_e = E @ enc.questions([q])[0].astype(np.float32)
            l_e = top_k(s_e, CONFIG["fusion"]["top_k"])
            if bm is None:
                return l_e
            s_b = bm.scores(q)
            l_b = top_k(s_b, CONFIG["fusion"]["top_k"]) if s_b is not None else []
            return rrf(l_b, l_e)[0]
        return f

    variantes = {
        "B commun (mE5-base, BM25 EN)": liste_commune(bm_en),
        "C commun (mE5-base, BM25 FR)": liste_commune(bm_fr),
        "D commun (mE5-base, E5 seul)": liste_commune(None),
    }

    lignes = []
    for nom_jeu, questions in jeux.items():
        avec = [q for q in questions if q["pertinents"]]
        hs = [q for q in questions if not q["pertinents"]]
        print(f"\n== {nom_jeu} : {len(avec)} questions avec réponse, {len(hs)} hors sujet")
        print(f"{'variante':<32}{'':>4}{'R@1':>7}{'R@3':>7}{'MRR@10':>9}   hors sujet rejetés")
        for nom, liste in variantes.items():
            avant, apres, rejets = [], [], 0
            for q in questions:
                l = liste(q["question"])
                ordre, mx = reranke(q["question"], l[:N_CAND])
                if q["pertinents"]:
                    pert = set(q["pertinents"])
                    avant.append(premier_rang([ids[i] for i in l], pert))
                    apres.append(premier_rang([ids[i] for i in ordre], pert))
                else:
                    rejets += mx < PLANCHER
            for etape, rangs in (("sans reranker", avant), ("+ reranker", apres)):
                r1, r3, mrr = resume(rangs)
                rej = f"{rejets}/{len(hs)}" if etape == "+ reranker" else ""
                print(f"{nom:<32}{etape:>14}  {r1:.3f}  {r3:.3f}  {mrr:.3f}   {rej}")
                lignes.append({"jeu": nom_jeu, "variante": nom, "etape": etape, "R@1": round(r1, 3), "R@3": round(r3, 3),
                               "MRR@10": round(mrr, 3), "hors_sujet_rejetes": rej})

    sortie = DOSSIER / "results/evaluation_video_commun.csv"   # evaluation_video.csv garde la variante A
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print(f"\n-> {sortie}")


if __name__ == "__main__":
    main()
