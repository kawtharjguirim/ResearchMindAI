"""Compare des versions du prompt de generation (rag.construire_prompt) pour un meme LLM.

Pour chaque question (eval/jeu_corpus.json, lot de validation par defaut), les extraits sont
recherches UNE fois puis donnes a chaque version du prompt : seule la consigne change.

Mesures par version :
  ROUGE-L    ressemblance avec la reponse de reference (0 a 1)
  ancrage    recouvrement lexical max de la reponse par un extrait fourni
  cite [n]   la reponse indique le numero d'un extrait
  anglais    la reponse est en anglais (consigne non respectee)
  refus      la reponse dit ne pas pouvoir repondre, separe en :
             - refus a tort    : le bon passage etait dans les extraits (il fallait repondre)
             - refus justifie  : le bon passage n'y etait pas (refuser est le bon comportement)
  ROUGE-L et ancrage sont calcules sur les questions dont le bon passage est dans les extraits.
  temps      secondes par reponse

Usage :
  python -I comparer_prompts.py [--versions v1 v2 v3] [--split validation|test] [--modele qwen2.5:3b] [--limite N]
Sorties : results/comparaison_prompts_<split>.csv et _reponses.json
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

REFUS = re.compile(r"ne (permettent|permet) pas|pas possible de r[ée]pondre|aucune information|ne (contiennent|contient) pas", re.I)
CITATION = re.compile(r"\[\d+\]")
MOTS_ANGLAIS = {"the", "and", "of", "is", "are", "to", "in", "that", "this", "with", "for"}


def en_anglais(texte):
    mots = re.findall(r"[a-zA-Z']+", texte.lower())
    return len(mots) > 5 and sum(m in MOTS_ANGLAIS for m in mots) / len(mots) > 0.12


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--versions", nargs="+", default=["v1", "v2", "v3"])
    p.add_argument("--split", choices=["validation", "test"], default="validation")
    p.add_argument("--modele", default=ragmod.MODELE_LLM)
    p.add_argument("--limite", type=int, default=0)
    args = p.parse_args()

    jeu = json.loads((DOSSIER / "eval/jeu_corpus.json").read_text(encoding="utf-8"))
    questions = [q for q in jeu["questions"] if q["statut"] in {"valide", "corrige"} and q["split"] == args.split]
    if args.limite:
        questions = questions[:args.limite]
    print(f"{len(questions)} questions ({args.split}) | modele {args.modele} | versions {args.versions}")

    stats = {v: {"rouge": [], "ancrage": [], "cite": 0, "anglais": 0, "refus_tort": 0, "refus_justifie": 0,
                 "vides": 0, "temps": []} for v in args.versions}
    detail = []
    partiel = DOSSIER / f"results/comparaison_prompts_{args.split}_{'_'.join(args.versions)}_partiel.json"
    for k, q in enumerate(questions, 1):
        passages = ragmod.search(q["question"], 5)
        present = q["chunk_id"] in {x["chunk_id"] for x in passages}
        ligne = {"id": q["id"], "question": q["question"], "reference": q["reference"],
                 "passage_attendu_dans_contexte": present, "reponses": {}}
        for v in args.versions:
            prompt = ragmod.construire_prompt(q["question"], passages, version=v)
            t0 = time.perf_counter()
            rep = ""
            for _ in range(3):
                try:
                    rep = ragmod._appeler_ollama(prompt, modele=args.modele)
                    break
                except Exception:  # noqa: BLE001 : Ollama peut echouer ponctuellement ; on reessaie
                    time.sleep(10)
            dt = time.perf_counter() - t0
            s = stats[v]
            s["temps"].append(dt)
            s["vides"] += not rep
            refus = bool(REFUS.search(rep))
            if present:
                s["rouge"].append(rouge_l(rep, q["reference"])["f1"])
                s["ancrage"].append(max((ragmod.couverture(rep, x["text"]) for x in passages), default=0.0))
                s["refus_tort"] += refus
                s["cite"] += bool(CITATION.search(rep)) and not refus
            else:
                s["refus_justifie"] += refus
            s["anglais"] += en_anglais(rep)
            ligne["reponses"][v] = {"reponse": rep, "temps_s": round(dt, 1)}
        detail.append(ligne)
        partiel.write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")   # survit a une coupure
        print(f"  [{k}/{len(questions)}] {q['id']} " + " | ".join(f"{v}: {ligne['reponses'][v]['temps_s']}s" for v in args.versions), flush=True)

    n = len(questions)
    contexte_ok = sum(l["passage_attendu_dans_contexte"] for l in detail)
    lignes = []
    print(f"\nPassage attendu dans les 5 extraits : {contexte_ok}/{n}")
    absents = n - contexte_ok
    moy = lambda xs: round(sum(xs) / len(xs), 4) if xs else 0.0  # noqa: E731
    print(f"{'version':<9}{'ROUGE-L':>9}{'ancrage':>9}{'cite':>8}{'refus a tort':>14}{'refus justifie':>16}{'anglais':>9}{'s/rep.':>8}")
    for v, s in stats.items():
        r = {"version": v, "modele": args.modele, "split": args.split, "questions": n,
             "rouge_l_f1": moy(s["rouge"]), "ancrage": moy(s["ancrage"]),
             "cite": f"{s['cite']}/{contexte_ok}", "refus_a_tort": f"{s['refus_tort']}/{contexte_ok}",
             "refus_justifie": f"{s['refus_justifie']}/{absents}", "anglais": f"{s['anglais']}/{n}",
             "vides": s["vides"], "secondes_par_reponse": round(sum(s["temps"]) / n, 1),
             "passage_attendu_dans_contexte": f"{contexte_ok}/{n}"}
        lignes.append(r)
        print(f"{v:<9}{r['rouge_l_f1']:>9.3f}{r['ancrage']:>9.3f}{r['cite']:>8}{r['refus_a_tort']:>14}{r['refus_justifie']:>16}{r['anglais']:>9}{r['secondes_par_reponse']:>8.1f}")

    base = DOSSIER / f"results/comparaison_prompts_{args.split}"
    base.with_name(base.name + "_reponses.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(base.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print(f"-> {base.with_suffix('.csv')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
