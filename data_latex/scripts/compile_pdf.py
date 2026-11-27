"""Compile des articles (data/tex/<domaine>/<id>) en PDF avec pdflatex -no-shell-escape.

Chaque article est copie dans data/build/<domaine>/<id> avant compilation (les sources
extraites ne sont pas modifiees). PDF -> data/pdf/<domaine>/<id>.pdf, rapport -> report.csv
Usage : python -I compile_pdf.py <pdflatex.exe> <data> <domaine> <id> [<id> ...]
"""
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT = 120


def find_main(folder):
    best = None
    for p in folder.rglob("*.tex"):
        try:
            s = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "\\documentclass" in s and "\\begin{document}" in s:
            depth = len(p.relative_to(folder).parts)
            if best is None or depth < best[0]:
                best = (depth, p)
    return best[1] if best else None


def first_error(log):
    if not log.exists():
        return ""
    txt = log.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^!.*$", txt, re.M)
    return m.group(0)[:150] if m else ""


def compile_one(pdflatex, src, build, pdf_dir, art_id):
    if build.exists():
        shutil.rmtree(build)
    shutil.copytree(src, build)
    main = find_main(build)
    if main is None:
        return "aucun fichier principal", ""
    for _ in range(2):
        try:
            subprocess.run(
                [pdflatex, "-no-shell-escape", "-interaction=nonstopmode", main.name],
                cwd=main.parent, capture_output=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return "timeout", ""
    pdf = main.with_suffix(".pdf")
    err = first_error(main.with_suffix(".log"))
    if pdf.exists():
        pdf_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, pdf_dir / f"{art_id}.pdf")
        return "ok" if not err else "ok (avec erreurs)", err
    return "echec", err


def main():
    pdflatex, data, dom, ids = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4:]
    rows = []
    for art_id in ids:
        status, err = compile_one(pdflatex, data / "tex" / dom / art_id,
                                  data / "build" / dom / art_id, data / "pdf" / dom, art_id)
        print(art_id, status, err, flush=True)
        rows.append({"id": art_id, "status": status, "first_error": err})
    with open(data / "pdf" / dom / "report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "status", "first_error"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
