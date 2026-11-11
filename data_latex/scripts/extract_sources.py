"""Extrait les source.bin (tar.gz / gz / pdf) vers <sortie>/<domaine>/<id>/ de facon sure.

Les archives sont non fiables : pas d'extraction hors du dossier cible, seulement des
fichiers normaux, taille limitee. Les archives brutes ne sont pas modifiees.
Usage : python -I extract_sources.py <data/raw> <data/tex> [domaine ...]
"""
import gzip
import io
import sys
import tarfile
from pathlib import Path

MAX_FILE = 50 * 1024 * 1024
MAX_TOTAL = 300 * 1024 * 1024
MAX_FILES = 2000


def safe_extract(tar, dest):
    total = count = 0
    root = dest.resolve()
    for m in tar:
        if not m.isfile():
            continue
        target = (dest / m.name).resolve()
        if root not in target.parents or m.size > MAX_FILE:
            continue
        total += m.size
        count += 1
        if total > MAX_TOTAL or count > MAX_FILES:
            raise ValueError("archive trop grosse")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(tar.extractfile(m).read())
    return count


def extract(src, dest):
    raw = src.read_bytes()
    if raw[:4] == b"%PDF":
        return "pdf seul (ignore)"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            n = safe_extract(tar, dest)
        return f"ok ({n} fichiers)"
    except tarfile.ReadError:
        data = gzip.decompress(raw)
        if len(data) > MAX_FILE:
            return "trop gros"
        (dest / "main.tex").write_bytes(data)
        return "ok (1 fichier)"


def main():
    raw_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
    wanted = set(sys.argv[3:])
    for dom in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        if wanted and dom.name not in wanted:
            continue
        stats = {}
        for art in sorted(p for p in dom.iterdir() if p.is_dir()):
            src = art / "source.bin"
            if not src.exists():
                continue
            dest = out / dom.name / art.name
            if dest.exists():
                status = "deja la"
            else:
                try:
                    status = extract(src, dest)
                except Exception as e:
                    status = f"erreur {type(e).__name__}"
            key = status.split(" (")[0]
            stats[key] = stats.get(key, 0) + 1
        print(dom.name, stats)


if __name__ == "__main__":
    main()
