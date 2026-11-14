"""Assemble le jeu de test du corpus (eval/jeu_corpus.json) a partir de l'echantillon de passages
(echantillonner.py) et des questions ecrites par domaine (eval/questions/<domaine>.json).

Chaque question vise un passage precis (chunk_id). Repartition validation / test stratifiee par
domaine (graine fixe). Relancer le script conserve le statut, les corrections et les commentaires
deja saisis (page Evaluation de l'application) : rien n'est ecrase.

Usage :
  python -I assembler_jeu.py [--part-validation 0.4] [--graine 42]
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "jeu_corpus.json"
EXCLUS = {
    "2503.03128_0011": "Texte d'exemple du gabarit LaTeX de la conférence, pas du contenu scientifique.",
    "2510.07844_0012": "Passage presque entièrement composé de remerciements et de financements.",
}
CHAMPS_SAISIS = ("statut", "question", "reference", "commentaire")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--part-validation", type=float, default=0.4)
    p.add_argument("--graine", type=int, default=42)
    args = p.parse_args()

    passages = json.loads((DOSSIER / "passages_echantillon.json").read_text(encoding="utf-8"))
    questions = {}
    for f in sorted((DOSSIER / "questions").glob("*.json")):
        questions.update(json.loads(f.read_text(encoding="utf-8")))
    ancien = {}
    if SORTIE.exists():
        ancien = {e["chunk_id"]: e for e in json.loads(SORTIE.read_text(encoding="utf-8"))["questions"]}

    par_domaine = defaultdict(list)
    manquants = []
    for ps in passages:
        if ps["chunk_id"] in EXCLUS:
            continue
        if ps["chunk_id"] not in questions:
            manquants.append(ps["chunk_id"])
            continue
        par_domaine[ps["domaine"]].append(ps)

    rng = random.Random(args.graine)
    entrees = []
    for domaine in sorted(par_domaine):
        lot = sorted(par_domaine[domaine], key=lambda x: x["chunk_id"])
        rng.shuffle(lot)
        n_val = round(len(lot) * args.part_validation)
        for i, ps in enumerate(sorted(lot[:n_val], key=lambda x: x["chunk_id"]) +
                               sorted(lot[n_val:], key=lambda x: x["chunk_id"])):
            q, ref = questions[ps["chunk_id"]]
            e = {"id": f"{domaine}-{i + 1:02d}", "domaine": domaine, "split": "validation" if i < n_val else "test",
                 "document_id": ps["document_id"], "chunk_id": ps["chunk_id"],
                 "question": q, "reference": ref, "question_initiale": q, "reference_initiale": ref,
                 "auteur": "claude", "statut": "a_valider", "commentaire": ""}
            e.update({k: ancien[ps["chunk_id"]][k] for k in CHAMPS_SAISIS if ps["chunk_id"] in ancien})
            entrees.append(e)

    jeu = {
        "description": "Jeu de test sur les 139 articles arXiv du corpus : une question en français par passage, "
                       "réponse de référence fidèle au passage. Questions écrites par Claude, à valider par un humain.",
        "pertinence": "Un seul passage pertinent par question (chunk_id). D'autres passages du même article peuvent "
                      "aussi répondre : les métriques sont donc une borne basse.",
        "statuts": {"a_valider": "pas encore relue", "valide": "acceptée telle quelle",
                    "corrige": "acceptée après correction", "rejete": "écartée de l'évaluation"},
        "exclus": [{"chunk_id": c, "raison": r} for c, r in EXCLUS.items()],
        "questions": entrees,
    }
    SORTIE.write_text(json.dumps(jeu, ensure_ascii=False, indent=1), encoding="utf-8")
    compte = defaultdict(lambda: defaultdict(int))
    for e in entrees:
        compte[e["domaine"]][e["split"]] += 1
    print(f"{len(entrees)} questions -> {SORTIE}")
    for d, c in compte.items():
        print(f"  {d:<13} validation {c['validation']:>2} | test {c['test']:>2}")
    if manquants:
        print("Passages sans question :", manquants)


if __name__ == "__main__":
    main()
