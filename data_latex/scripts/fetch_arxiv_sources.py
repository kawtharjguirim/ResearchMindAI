"""Choisit N articles (cs.CL / cs.IR, CC BY / CC BY-SA / CC0) et telecharge leurs sources.

- Lit le JSON ligne par ligne (jamais en entier en memoire).
- Echantillon reproductible (seed fixe), articles recents (id YYMM.NNNNN, annee >= 2019).
- 1 requete toutes les 3 s. Les archives sont sauvegardees telles quelles (non extraites).
Usage : python -I fetch_arxiv_sources.py <snapshot.json> <dossier_sortie> [N]
"""
import csv
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OK_LICENSES = {
    "http://creativecommons.org/licenses/by/4.0/",
    "http://creativecommons.org/licenses/by/3.0/",
    "http://creativecommons.org/licenses/by-sa/4.0/",
    "http://creativecommons.org/licenses/by-sa/3.0/",
    "http://creativecommons.org/publicdomain/zero/1.0/",
}
NEW_ID = re.compile(r"^(\d{2})(\d{2})\.\d{4,5}$")
DELAY = 3.0
UA = "ResearchMindAI-student-project/0.1"


def sample_candidates(snapshot, n, seed=42):
    rng = random.Random(seed)
    pool, seen = [], 0
    with open(snapshot, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            m = NEW_ID.match(d["id"])
            if not m or int(m.group(1)) < 19:
                continue
            cats = d["categories"].split()
            if not ({"cs.CL", "cs.IR"} & set(cats)) or d.get("license") not in OK_LICENSES:
                continue
            row = {"id": d["id"], "title": " ".join(d["title"].split()),
                   "categories": d["categories"], "license": d["license"]}
            seen += 1
            if len(pool) < n:  # reservoir sampling
                pool.append(row)
            else:
                j = rng.randrange(seen)
                if j < n:
                    pool[j] = row
    print(f"{seen} candidats eligibles, {len(pool)} tires au sort")
    return sorted(pool, key=lambda r: r["id"])


def download(arxiv_id, dest):
    req = urllib.request.Request(f"https://arxiv.org/e-print/{arxiv_id}", headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                ctype = r.headers.get("Content-Type", "")
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "source.bin").write_bytes(data)
            return f"ok ({len(data)} o, {ctype})"
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            return f"erreur HTTP {e.code}"
        except Exception as e:  # reseau
            if attempt == 2:
                return f"erreur {type(e).__name__}"
            time.sleep(10)
    return "echec 429"


def main():
    snapshot, out = Path(sys.argv[1]), Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    out.mkdir(parents=True, exist_ok=True)
    rows = sample_candidates(snapshot, n)
    with open(out / "manifest.csv", "w", newline="", encoding="utf-8") as mf:
        w = csv.DictWriter(mf, fieldnames=["id", "title", "categories", "license", "status"])
        w.writeheader()
        for i, row in enumerate(rows, 1):
            dest = out / row["id"].replace("/", "_")
            if (dest / "source.bin").exists():
                row["status"] = "deja la"
            else:
                row["status"] = download(row["id"], dest)
                time.sleep(DELAY)
            w.writerow(row)
            mf.flush()
            print(f"[{i}/{len(rows)}] {row['id']} {row['status']}", flush=True)


if __name__ == "__main__":
    main()
