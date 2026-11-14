"""Evaluation du retrieval sur notre corpus (139 articles arXiv) avec eval/jeu_corpus.json.

Mesure chaque etape du moteur de recherche (BM25, E5, fusion RRF, fusion + reranker) sur les
memes questions : Recall@1/@3/@10, MRR@10, nDCG@10 (un seul passage pertinent par question,
donc nDCG@10 = 1/log2(rang + 1) si le passage est dans le top 10). Par defaut, seules les
questions validees par un humain (statut valide ou corrige) sont comptees.

Usage :
  python -I evaluation_corpus.py [--split test|validation|tout] [--toutes]
Sorties : results/evaluation_corpus.csv (+ _par_domaine.csv)
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
from recherche import CONFIG, N_CANDIDATS, Index  # noqa: E402

STATUTS_VALIDES = {"valide", "corrige"}


def rang(classement, cible):
    """Rang (1 = premier) du passage pertinent dans un classement de chunk_id, ou None."""
    try:
        return classement.index(cible) + 1
    except ValueError:
        return None


def metriques(rangs):
    n = len(rangs)
    def part(k):
        return sum(1 for r in rangs if r and r <= k) / n
    return {"n": n, "Recall@1": part(1), "Recall@3": part(3), "Recall@10": part(10),
            "MRR@10": sum(1 / r for r in rangs if r and r <= 10) / n,
            "nDCG@10": sum(1 / math.log2(r + 1) for r in rangs if r and r <= 10) / n}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=["test", "validation", "tout"], default="test")
    p.add_argument("--toutes", action="store_true", help="inclure les questions pas encore validees")
    args = p.parse_args()

    jeu = json.loads((DOSSIER / "eval/jeu_corpus.json").read_text(encoding="utf-8"))
    questions = [q for q in jeu["questions"]
                 if q["statut"] != "rejete"
                 and (args.toutes or q["statut"] in STATUTS_VALIDES)
                 and (args.split == "tout" or q["split"] == args.split)]
    if not questions:
        print("Aucune question retenue : validez des questions dans la page Evaluation, ou utilisez --toutes.")
        return 1
    non_validees = sum(q["statut"] not in STATUTS_VALIDES for q in questions)
    print(f"{len(questions)} questions (split {args.split}, dont {non_validees} non validees)")

    chunks = [json.loads(l) for l in open(DOSSIER / "data/chunks.jsonl", encoding="utf-8")]
    index = Index(chunks)
    ids = index.ids

    systemes = ["BM25", "E5", "Hybride RRF", f"Hybride + reranker (top {N_CANDIDATS})"]
    rangs = defaultdict(list)
    par_domaine = defaultdict(lambda: defaultdict(list))
    latences = []
    for q in questions:
        t0 = time.perf_counter()
        c = index.classements(q["question"])
        reclasses = [r["chunk"]["chunk_id"] for r in index.rechercher(q["question"])]
        latences.append(time.perf_counter() - t0)
        classements = {"BM25": [ids[i] for i in c["BM25"]], "E5": [ids[i] for i in c["E5"]],
                       "Hybride RRF": [ids[i] for i in c["Hybride RRF"]], systemes[3]: reclasses}
        for s in systemes:
            r = rang(classements[s], q["chunk_id"])
            rangs[s].append(r)
            par_domaine[q["domaine"]][s].append(r)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    portee = "toutes (non validees incluses)" if args.toutes else "validees uniquement"
    lignes = []
    print(f"\n{'systeme':<32} {'R@1':>6} {'R@3':>6} {'R@10':>6} {'MRR@10':>7} {'nDCG@10':>8}")
    for s in systemes:
        m = metriques(rangs[s])
        print(f"{s:<32} {m['Recall@1']:>6.3f} {m['Recall@3']:>6.3f} {m['Recall@10']:>6.3f} {m['MRR@10']:>7.3f} {m['nDCG@10']:>8.3f}")
        lignes.append({"date": date, "split": args.split, "questions": portee, "systeme": s,
                       "modele_embedding": CONFIG["embedding"]["modele"], "reranker": CONFIG["reranker"]["modele"],
                       **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}})
    print(f"\nLatence moyenne recherche + reranking : {1000 * sum(latences) / len(latences):.0f} ms / question")

    sortie = DOSSIER / "results/evaluation_corpus.csv"
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    with open(DOSSIER / "results/evaluation_corpus_par_domaine.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "split", "questions", "domaine", "systeme", "n", "Recall@10", "MRR@10", "nDCG@10"])
        for d in sorted(par_domaine):
            for s in systemes:
                m = metriques(par_domaine[d][s])
                w.writerow([date, args.split, portee, d, s, m["n"], round(m["Recall@10"], 4),
                            round(m["MRR@10"], 4), round(m["nDCG@10"], 4)])
    print(f"-> {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
