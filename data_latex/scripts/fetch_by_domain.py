"""Tire N articles par domaine (CC BY / CC BY-SA / CC0, >= 2019) et telecharge leurs sources.

Domaine = categorie principale arXiv (la premiere de la liste).
Rangement : <sortie>/<domaine>/<id>/source.bin + <sortie>/<domaine>/manifest.csv
Lecture du JSON ligne par ligne, 1 requete toutes les 3 s (tous domaines confondus).
Usage : python -I fetch_by_domain.py <snapshot.json> <dossier_sortie> <N par domaine> <domaine> [<domaine> ...]
"""
import csv
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # utile avec python -I

from fetch_arxiv_sources import DELAY, NEW_ID, OK_LICENSES, download

PREFIXES = {
    "physique": ("astro-ph", "cond-mat", "gr-qc", "hep-", "nucl-", "quant-ph", "nlin", "physics"),
    "maths": ("math",),
    "statistiques": ("stat",),
    "biologie": ("q-bio",),
    "finance-eco": ("q-fin", "econ", "eess"),
}


def domain_of(primary):
    for dom, prefixes in PREFIXES.items():
        if primary.startswith(prefixes):
            return dom
    return None


def sample(snapshot, domains, n, seed=42):
    rng = random.Random(seed)
    pools = {d: [] for d in domains}
    seen = {d: 0 for d in domains}
    with open(snapshot, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            m = NEW_ID.match(d["id"])
            if not m or int(m.group(1)) < 19 or d.get("license") not in OK_LICENSES:
                continue
            dom = domain_of(d["categories"].split()[0])
            if dom not in pools:
                continue
            row = {"id": d["id"], "title": " ".join(d["title"].split()),
                   "categories": d["categories"], "license": d["license"]}
            seen[dom] += 1
            if len(pools[dom]) < n:  # reservoir sampling
                pools[dom].append(row)
            else:
                j = rng.randrange(seen[dom])
                if j < n:
                    pools[dom][j] = row
    for dom in domains:
        print(f"{dom}: {seen[dom]} candidats eligibles, {len(pools[dom])} tires", flush=True)
    return {d: sorted(p, key=lambda r: r["id"]) for d, p in pools.items()}


def main():
    snapshot, out, n = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    domains = sys.argv[4:]
    unknown = [d for d in domains if d not in PREFIXES]
    if unknown:
        sys.exit(f"domaine inconnu : {unknown}")
    pools = sample(snapshot, domains, n)
    for dom in domains:
        ddir = out / dom
        ddir.mkdir(parents=True, exist_ok=True)
        with open(ddir / "manifest.csv", "w", newline="", encoding="utf-8") as mf:
            w = csv.DictWriter(mf, fieldnames=["id", "title", "categories", "license", "status"])
            w.writeheader()
            for i, row in enumerate(pools[dom], 1):
                dest = ddir / row["id"]
                if (dest / "source.bin").exists():
                    row["status"] = "deja la"
                else:
                    row["status"] = download(row["id"], dest)
                    time.sleep(DELAY)
                w.writerow(row)
                mf.flush()
                print(f"[{dom} {i}/{len(pools[dom])}] {row['id']} {row['status']}", flush=True)


if __name__ == "__main__":
    main()
