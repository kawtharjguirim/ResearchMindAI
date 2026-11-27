"""Evalue la recherche (Recall@1, Recall@3, MRR@10) et la generation RAG (ROUGE-1/2/L)
sur un petit jeu de questions annotees.

Le corpus ne contient pas de reponses de reference ecrites par un humain : les questions
de rag/eval/eval_questions.json et leurs reponses de reference ("reference") ont ete
redigees a la main pour cette mission, a partir du contenu reel du (des) chunk(s)
pertinent(s) indique(s) pour chaque question. C'est un jeu d'evaluation volontairement
petit et illustratif (5 questions), pas un jeu de validation complet -- voir le rapport
de fin de mission pour le detail de cette limite.

Usage :
  python -I evaluation.py --chunks data/chunks.jsonl --questions eval/eval_questions.json
Sorties :
  results/resultats_retrieval.csv, results/resultats_rouge.csv, eval/reponses_rag.json
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # utile avec python -I
import rag as ragmod  # noqa: E402
from rouge import rouge  # noqa: E402

N_CANDIDATS_METRIQUES = 10


def rang_premier_pertinent(classement_ids, pertinents):
    """Rang (1-based) du premier chunk pertinent dans le classement, ou None si absent."""
    for r, cid in enumerate(classement_ids, start=1):
        if cid in pertinents:
            return r
    return None


def resume_rangs(rangs):
    n = len(rangs)
    return {"Recall@1": sum(1 for x in rangs if x and x <= 1) / n,
            "Recall@3": sum(1 for x in rangs if x and x <= 3) / n,
            "MRR@10": sum(1 / x for x in rangs if x) / n}


def moyenne_rouge(liste_scores):
    """Moyenne des f1 ROUGE-1/2/L sur une liste de resultats de rouge()."""
    return {cle: sum(d[cle]["f1"] for d in liste_scores) / len(liste_scores)
            for cle in ("rouge-1", "rouge-2", "rouge-l")}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chunks", default=str(Path(__file__).resolve().parent / "data" / "chunks.jsonl"))
    p.add_argument("--questions", default=str(Path(__file__).resolve().parent / "eval" / "eval_questions.json"))
    p.add_argument("--out-dir", default=str(Path(__file__).resolve().parent / "results"))
    p.add_argument("--reponses-json", default=str(Path(__file__).resolve().parent / "eval" / "reponses_rag.json"))
    args = p.parse_args()

    questions = json.load(open(args.questions, encoding="utf-8"))
    index = ragmod.charger_index(args.chunks)
    ids = index.ids

    rangs = {"BM25": [], "E5": [], "Hybride RRF": [], "Hybride + MiniLM": []}
    journal = []

    for k, q in enumerate(questions, start=1):
        print(f"[{k}/{len(questions)}] {q['question']}", flush=True)
        pert = set(q["pertinents"])

        c = index.classements(q["question"])
        for nom, cle in (("BM25", "BM25"), ("E5", "E5"), ("Hybride RRF", "Hybride RRF")):
            rangs[nom].append(rang_premier_pertinent([ids[i] for i in c[cle][:N_CANDIDATS_METRIQUES]], pert))

        resultats = index.rechercher(q["question"], n=N_CANDIDATS_METRIQUES)
        classement_reranke = [ids[r["idx"]] for r in resultats]
        rangs["Hybride + MiniLM"].append(rang_premier_pertinent(classement_reranke, pert))

        t0 = time.time()
        rep = ragmod.answer(q["question"])
        duree = time.time() - t0
        scores_rouge = rouge(rep["reponse"], q["reference"])

        journal.append({
            "question": q["question"], "domaine": q.get("domaine", ""),
            "reference": q["reference"], "pertinents": sorted(pert),
            "rang_bon_passage": rang_premier_pertinent(classement_reranke, pert),
            "reponse": rep["reponse"], "citations": rep["citations"], "verifie": rep["verifie"],
            "rouge": scores_rouge, "temps_generation_s": round(duree, 1),
            "relecture_manuelle": {"fidele": None, "repond_a_la_question": None, "commentaire": ""},
        })

    # ---------- Retrieval ----------
    print("\nRecherche (retrieval) :")
    print(f"  {'systeme':<20}{'Recall@1':>10}{'Recall@3':>10}{'MRR@10':>9}")
    lignes_retrieval = [["systeme", "recall@1", "recall@3", "mrr@10"]]
    for systeme, r in rangs.items():
        res = resume_rangs(r)
        print(f"  {systeme:<20}{res['Recall@1']:>10.2f}{res['Recall@3']:>10.2f}{res['MRR@10']:>9.3f}")
        lignes_retrieval.append([systeme, round(res["Recall@1"], 3), round(res["Recall@3"], 3),
                                 round(res["MRR@10"], 3)])

    # ---------- ROUGE ----------
    print("\nGeneration (ROUGE, moyenne f1 sur les reponses non rejetees) :")
    non_rejetees = [j for j in journal if j["citations"]]
    moy = moyenne_rouge([j["rouge"] for j in non_rejetees]) if non_rejetees else \
        {"rouge-1": 0.0, "rouge-2": 0.0, "rouge-l": 0.0}
    lignes_rouge = [["metrique", "f1_moyen"]]
    for cle, val in moy.items():
        print(f"  {cle:<10}{val:.3f}")
        lignes_rouge.append([cle, round(val, 3)])
    print(f"  (sur {len(non_rejetees)}/{len(questions)} reponses non rejetees)")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "resultats_retrieval.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(lignes_retrieval)
    with open(out_dir / "resultats_rouge.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(lignes_rouge)
    with open(args.reponses_json, "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)

    print(f"\nResultats -> {out_dir}  |  reponses a relire -> {args.reponses_json}")


if __name__ == "__main__":
    main()
