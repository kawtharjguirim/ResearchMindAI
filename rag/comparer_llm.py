"""Compare plusieurs LLM (Ollama) pour la generation du RAG, a contexte identique.

Pour chaque question du jeu de test (eval/jeu_corpus.json, lot de validation par defaut) :
les passages sont recherches UNE fois, puis le meme prompt (rag.construire_prompt) est donne a
chaque modele. Le raisonnement des modeles « R1 » (<think>...</think>) est retire avant notation.

Mesures par modele :
  ROUGE-L F1      reponse vs reponse de reference du jeu de test
  ancrage         couverture lexicale max de la reponse par un passage fourni (comme rag.answer)
  refus           la reponse dit ne pas pouvoir repondre
  temps           secondes par reponse (raisonnement compris)
Le passage attendu est-il dans le contexte ? (meme valeur pour tous les modeles : retrieval)

Usage :
  python -I comparer_llm.py --modeles qwen2.5:3b deepseek-r1:1.5b [--split validation] [--toutes] [--limite N]
Sorties : results/comparaison_llm.csv (resume), results/comparaison_llm_reponses.json (detail)
"""
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER))
import rag as ragmod  # noqa: E402
from rouge import rouge_l  # noqa: E402

STATUTS_VALIDES = {"valide", "corrige"}
REFUS = re.compile(r"ne (permettent|permet) pas|pas possible de r[ée]pondre|aucune information|ne (contiennent|contient) pas", re.I)


def sans_raisonnement(texte):
    texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.S)
    return texte.split("</think>")[-1].strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modeles", nargs="+", required=True)
    p.add_argument("--split", choices=["validation", "test", "tout"], default="validation")
    p.add_argument("--toutes", action="store_true", help="inclure les questions pas encore validees")
    p.add_argument("--limite", type=int, default=0)
    p.add_argument("--num-predict", type=int, default=200, help="jetons de reponse (hors raisonnement)")
    p.add_argument("--num-predict-raisonnement", type=int, default=1000, help="budget total des modeles R1")
    args = p.parse_args()

    jeu = json.loads((DOSSIER / "eval/jeu_corpus.json").read_text(encoding="utf-8"))
    questions = [q for q in jeu["questions"] if q["statut"] != "rejete"
                 and (args.toutes or q["statut"] in STATUTS_VALIDES)
                 and (args.split == "tout" or q["split"] == args.split)]
    if args.limite:
        questions = questions[:args.limite]
    if not questions:
        print("Aucune question retenue (utilisez --toutes tant que le jeu n'est pas relu).")
        return 1
    print(f"{len(questions)} questions ({args.split}, dont {sum(q['statut'] not in STATUTS_VALIDES for q in questions)} non validees)")

    detail, stats = [], {m: {"rouge": [], "ancrage": [], "refus": 0, "temps": [], "vides": 0, "erreurs": 0} for m in args.modeles}
    contexte_ok = 0
    for k, q in enumerate(questions, 1):
        passages = ragmod.search(q["question"], 5)
        contexte_ok += q["chunk_id"] in {x["chunk_id"] for x in passages}
        prompt = ragmod.construire_prompt(q["question"], passages)
        ligne = {"id": q["id"], "question": q["question"], "reference": q["reference"],
                 "passage_attendu_dans_contexte": q["chunk_id"] in {x["chunk_id"] for x in passages}, "reponses": {}}
        for m in args.modeles:
            budget = args.num_predict_raisonnement if "r1" in m.lower() else args.num_predict
            t0 = time.perf_counter()
            brute, erreur = "", ""
            for essai in range(3):
                try:
                    brute = ragmod._appeler_ollama(prompt, num_predict=budget, modele=m)
                    break
                except Exception as e:  # noqa: BLE001 : Ollama peut echouer (memoire GPU) ; on note et on continue
                    erreur = f"{type(e).__name__}: {e}"
                    time.sleep(10)
            dt = time.perf_counter() - t0
            if not brute:
                stats[m]["erreurs"] += 1
            rep = sans_raisonnement(brute)
            s = stats[m]
            s["temps"].append(dt)
            if not rep:
                s["vides"] += 1
            s["rouge"].append(rouge_l(rep, q["reference"])["f1"])
            s["ancrage"].append(max((ragmod.couverture(rep, x["text"]) for x in passages), default=0.0))
            s["refus"] += bool(REFUS.search(rep))
            ligne["reponses"][m] = {"reponse": rep, "temps_s": round(dt, 1), "raisonnement_retire": rep != brute.strip(),
                                    "erreur": "" if brute else erreur}
        detail.append(ligne)
        print(f"  [{k}/{len(questions)}] {q['id']} " + " | ".join(f"{m}: {ligne['reponses'][m]['temps_s']}s" for m in args.modeles), flush=True)

    n = len(questions)
    lignes = []
    print(f"\nPassage attendu dans le contexte : {contexte_ok}/{n}")
    print(f"{'modele':<22}{'ROUGE-L':>9}{'ancrage':>9}{'refus':>7}{'vides':>7}{'s/rep.':>8}")
    for m, s in stats.items():
        r = {"modele": m, "split": args.split, "questions": n, "non_validees_incluses": args.toutes,
             "rouge_l_f1": round(sum(s["rouge"]) / n, 4), "ancrage": round(sum(s["ancrage"]) / n, 4),
             "refus": s["refus"], "reponses_vides": s["vides"], "erreurs_ollama": s["erreurs"], "secondes_par_reponse": round(sum(s["temps"]) / n, 1),
             "passage_attendu_dans_contexte": f"{contexte_ok}/{n}"}
        lignes.append(r)
        print(f"{m:<22}{r['rouge_l_f1']:>9.3f}{r['ancrage']:>9.3f}{s['refus']:>7}{s['vides']:>7}{r['secondes_par_reponse']:>8.1f}")

    (DOSSIER / "results/comparaison_llm_reponses.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(DOSSIER / "results/comparaison_llm.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print("-> results/comparaison_llm.csv, results/comparaison_llm_reponses.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
