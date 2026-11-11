"""Construit le document d'indexation : 1 ligne par article = metadonnees + PDF + code .tex.

Sortie : <data>/index/documents.jsonl (pour le RAG) et <data>/index/documents.csv (lisible).
Chemins relatifs a <data>. Le JSON du snapshot est lu ligne par ligne (jamais en entier),
uniquement pour recuperer le resume des articles retenus.
Usage : python -I build_index.py <data> <snapshot.json>
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # utile avec python -I
from compile_pdf import find_main  # noqa: E402

DOMAINS = ("informatique", "physique", "maths", "statistiques", "biologie", "finance-eco")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_abstracts(snapshot, ids):
    wanted, found = set(ids), {}
    with open(snapshot, encoding="utf-8") as f:
        for line in f:
            if not wanted:
                break
            if not line.startswith('{"id":"'):
                continue
            i = line[7:line.index('"', 7)]
            if i in wanted:
                d = json.loads(line)
                found[i] = {"abstract": " ".join(d["abstract"].split()),
                            "authors": " ".join(d["authors"].split()),
                            "update_date": d.get("update_date")}
                wanted.discard(i)
    return found


def main():
    data, snapshot = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    manifests = {}
    for dom in DOMAINS:
        with open(data / "raw" / dom / "manifest.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                manifests[row["id"]] = row
    docs = []
    for dom in DOMAINS:
        for pdf in sorted((data / "pdf" / dom).glob("*.pdf")):
            i = pdf.stem
            tex_dir = data / "tex" / dom / i
            if not tex_dir.is_dir():
                print("sans dossier tex :", dom, i)
                continue
            main_tex = find_main(tex_dir)
            tex_files = sorted(p for p in tex_dir.rglob("*.tex"))
            m = manifests.get(i, {})
            docs.append({
                "doc_id": i,
                "domain": dom,
                "title": m.get("title", ""),
                "categories": m.get("categories", ""),
                "license": m.get("license", ""),
                "arxiv_url": f"https://arxiv.org/abs/{i}",
                "pdf_path": pdf.relative_to(data).as_posix(),
                "pdf_bytes": pdf.stat().st_size,
                "pdf_sha256": sha256(pdf),
                "tex_dir": tex_dir.relative_to(data).as_posix(),
                "main_tex": main_tex.relative_to(data).as_posix() if main_tex else None,
                "tex_files": [p.relative_to(data).as_posix() for p in tex_files],
                "bib_files": [p.relative_to(data).as_posix() for p in tex_dir.rglob("*.bib")],
            })
    extra = load_abstracts(snapshot, [d["doc_id"] for d in docs])
    for d in docs:
        d.update(extra.get(d["doc_id"], {"abstract": "", "authors": "", "update_date": None}))
    out = data / "index"
    out.mkdir(exist_ok=True)
    with open(out / "documents.jsonl", "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    cols = ["doc_id", "domain", "title", "categories", "license", "pdf_path", "main_tex", "pdf_bytes"]
    with open(out / "documents.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(docs)
    print(len(docs), "documents indexes ->", out)
    print("sans fichier principal :", [d["doc_id"] for d in docs if not d["main_tex"]])
    print("sans resume :", [d["doc_id"] for d in docs if not d["abstract"]])


if __name__ == "__main__":
    main()
