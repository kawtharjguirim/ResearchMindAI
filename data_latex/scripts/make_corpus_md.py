"""Genere data/index/documents.md : liste lisible des PDF deja compiles, par domaine."""
import json
import sys
from collections import defaultdict
from pathlib import Path


def main():
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    docs = [json.loads(l) for l in open(data / "index" / "documents.jsonl", encoding="utf-8")]
    by_dom = defaultdict(list)
    for d in docs:
        by_dom[d["domain"]].append(d)

    lines = [
        "# Corpus arXiv traite - PDF compiles",
        "",
        f"Articles arXiv selectionnes (licences CC BY / CC BY-SA / CC0, 2019+, seed 42), "
        f"sources .tex telechargees, compilees en PDF avec `pdflatex -no-shell-escape`. "
        f"Total : **{len(docs)} / 532** articles compiles avec succes.",
        "",
    ]
    for dom in sorted(by_dom):
        rows = sorted(by_dom[dom], key=lambda d: d["doc_id"])
        lines.append(f"## {dom} ({len(rows)})")
        lines.append("")
        lines.append("| arXiv ID | Titre | Licence | Lien |")
        lines.append("|---|---|---|---|")
        for d in rows:
            parts = d["license"].rstrip("/").rsplit("/", 2)
            lic_short = "/".join(parts[-2:]) if len(parts) >= 2 else d["license"]
            title = d["title"].replace("|", "\\|")
            lines.append(f"| {d['doc_id']} | {title} | {lic_short} | [arXiv]({d['arxiv_url']}) |")
        lines.append("")

    out = data / "index" / "documents.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("ok", len(docs), "->", out)


if __name__ == "__main__":
    main()
