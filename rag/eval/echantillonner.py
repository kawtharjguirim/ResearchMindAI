"""Echantillon de passages du corpus pour ecrire le jeu de test (questions sur nos articles).

Tirage reproductible (graine fixe) et stratifie par domaine : N passages par domaine, au plus un
par article tant que le domaine a assez d'articles, puis un second. Ecarte les passages courts,
les remerciements / checklists / bibliographies, et ceux domines par les formules.

Usage :
  python -I echantillonner.py [--par-domaine 20] [--graine 42]
Sortie : eval/passages_echantillon.json
"""
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parents[1]
SECTIONS_EXCLUES = re.compile(r"acknowledg|checklist|reference|bibliograph|funding|author contribution", re.I)
MOTS_MIN = 120
DOLLARS_MAX = 10      # « $ » de formules en ligne
EQ_MAX = 2            # formules hors ligne remplacees par [EQ]


def utilisable(c):
    t = c["text"]
    return (len(t.split()) >= MOTS_MIN and not SECTIONS_EXCLUES.search(c.get("section", ""))
            and t.count("$") <= DOLLARS_MAX and t.count("[EQ]") <= EQ_MAX)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--par-domaine", type=int, default=20)
    p.add_argument("--graine", type=int, default=42)
    args = p.parse_args()

    docs = {}
    with open(RACINE / "data_latex/data/index/documents.jsonl", encoding="utf-8") as f:
        for ligne in f:
            d = json.loads(ligne)
            docs[d["doc_id"]] = d
    par_doc = defaultdict(list)
    with open(DOSSIER.parent / "data/chunks.jsonl", encoding="utf-8") as f:
        for ligne in f:
            c = json.loads(ligne)
            if c["source"] == "article" and c["document_id"] in docs and utilisable(c):
                par_doc[c["document_id"]].append(c)

    rng = random.Random(args.graine)
    par_domaine = defaultdict(list)
    for doc_id in sorted(par_doc):
        par_domaine[docs[doc_id]["domain"]].append(doc_id)

    echantillon = []
    for domaine in sorted(par_domaine):
        ids = par_domaine[domaine][:]
        rng.shuffle(ids)
        restants = {d: rng.sample(par_doc[d], len(par_doc[d])) for d in ids}
        choisis = []
        while len(choisis) < args.par_domaine and any(restants.values()):
            for d in ids:                       # un passage par article et par tour
                if restants[d] and len(choisis) < args.par_domaine:
                    choisis.append(restants[d].pop())
        for c in choisis:
            d = docs[c["document_id"]]
            echantillon.append({"chunk_id": c["chunk_id"], "document_id": c["document_id"], "domaine": domaine,
                                "titre": d["title"], "section": c.get("section", ""), "texte": c["text"]})

    sortie = DOSSIER / "passages_echantillon.json"
    sortie.write_text(json.dumps(echantillon, ensure_ascii=False, indent=1), encoding="utf-8")
    compte = defaultdict(int)
    for e in echantillon:
        compte[e["domaine"]] += 1
    print(f"{len(echantillon)} passages -> {sortie} : {dict(compte)}")


if __name__ == "__main__":
    main()
