"""Decoupe les sources .tex en chunks de texte et calcule leurs embeddings E5.

Pour chaque article de data/tex/<domaine>/<id>/ :
1. repere le fichier .tex principal (find_main, repris de compile_pdf.py) ;
2. en extrait le texte lisible (sections, texte normal, listes, equations inline),
   en retirant les commandes LaTeX de mise en forme/structure, les commentaires,
   la bibliographie et le contenu brut des figures/tableaux (seule la legende est gardee) ;
3. decoupe le texte de chaque section en chunks de 300 mots max, avec 20 % de
   recouvrement entre chunks consecutifs (fenetre glissante sur les mots, comme
   decouper.py mais sur du texte plat plutot que des segments horodates).

Sorties (dans <data>/index/) :
  - chunks.jsonl            : une ligne par chunk {chunk_id, doc_id, domain,
                              section_title, chunk_index, text}
  - chunks_embeddings.npy   : embeddings E5 (passage) des chunks, meme ordre
                              que chunks.jsonl (etape sautee si sentence-transformers
                              n'est pas installe : voir le message affiche).

Sources .tex non fiables : traitees en lecture seule, aucun code n'est execute.

Usage :
  python -I chunk_embed.py <data> [--domains d1 d2 ...] [--ids id1 id2 ...]
                                   [--limit N] [--no-embed] [--batch-size 32]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # utile avec python -I
from compile_pdf import find_main  # noqa: E402

DOMAINS = ("informatique", "physique", "maths", "statistiques", "biologie", "finance-eco")

MAX_MOTS = 300
RECOUVREMENT = 0.2  # 20 %

PREFIXE_E5 = "passage: "
MODELE_E5 = "intfloat/multilingual-e5-small"  # meme modele que backend/app/services/video/search.py

# commandes sans texte a retirer purement et simplement (switches de mise en forme, etc.)
_COMMANDES_SANS_ARG = (
    "maketitle", "noindent", "par", "newline", "linebreak", "pagebreak", "newpage",
    "clearpage", "tableofcontents", "appendix", "centering", "flushleft", "flushright",
    "smallskip", "medskip", "bigskip", "indent", "sloppy", "vfill", "hfill",
    "bigbreak", "medbreak", "smallbreak",
)

# commandes a un ou deux arguments qui ne portent pas de texte utile
_COMMANDES_ARG_SANS_TEXTE = (
    "input", "include", "bibliographystyle", "pagestyle", "thispagestyle",
)

_SYMBOLES = {
    r"\ldots": "...", r"\dots": "...", r"\LaTeX": "LaTeX", r"\TeX": "TeX",
    r"\BibTeX": "BibTeX",
}

_RE_SECTION = re.compile(r"\\(section|subsection|subsubsection)\*?\{((?:[^{}]|\{[^{}]*\})*)\}")
_RE_FLOAT = re.compile(r"\\begin\{(figure|table|wrapfigure|subfigure)\*?\}(.*?)\\end\{\1\*?\}", re.S)
_RE_CAPTION = re.compile(r"\\caption\{((?:[^{}]|\{[^{}]*\})*)\}", re.S)
_RE_CITE = re.compile(r"\\(?:cite\w*|textcite)(?:\[[^\]]*\])*\{[^}]*\}")
_RE_REF = re.compile(r"\\(?:eqref|autoref|pageref|ref)\{[^}]*\}")
_RE_LABEL = re.compile(r"\\label\{[^}]*\}")
_RE_ITEM = re.compile(r"\\item(?:\[[^\]]*\])?")
_RE_ACCENT = re.compile(r"\\[\'\`\"\^~Hvbcu\.=]\{([^{}]*)\}")
_RE_BRACE_CMD = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{((?:[^{}]|\{[^{}]*\})*)\}")
_RE_BARE_CMD = re.compile(r"\\[a-zA-Z]+\*?")
_RE_MATH_INLINE = re.compile(r"\$[^$\n]*\$")
_RE_FOOTNOTE = re.compile(r"\\footnote(?:text)?\{((?:[^{}]|\{[^{}]*\})*)\}")

# equations hors ligne (pas "telles quelles" comme les $...$ : gardees brutes, elles
# ne seraient que des debris une fois les commandes de style \alpha, \beta... retirees)
_ENV_MATH = (
    "equation", "align", "eqnarray", "gather", "multline", "flalign", "alignat",
    "cases", "matrix", "pmatrix", "bmatrix", "vmatrix", "Vmatrix", "array", "split",
)
_RE_MATH_ENV = re.compile(
    r"\\begin\{(" + "|".join(_ENV_MATH) + r")\*?\}.*?\\end\{\1\*?\}", re.S
)
_RE_MATH_BRACKETS = re.compile(r"\\\[.*?\\\]", re.S)
_RE_MATH_DOUBLE_DOLLAR = re.compile(r"\$\$.*?\$\$", re.S)

_ESCAPES = {r"\$": "$", r"\%": "%", r"\&": "&", r"\_": "_", r"\#": "#", r"\{": "{", r"\}": "}"}


def strip_comments(tex):
    """Retire les commentaires LaTeX (% jusqu'a la fin de la ligne, sauf \\%)."""
    lignes = []
    for ligne in tex.split("\n"):
        i = 0
        while True:
            j = ligne.find("%", i)
            if j == -1:
                lignes.append(ligne)
                break
            k, nb = j - 1, 0
            while k >= 0 and ligne[k] == "\\":
                nb += 1
                k -= 1
            if nb % 2 == 0:  # % non echappe : debut de commentaire
                lignes.append(ligne[:j])
                break
            i = j + 1
    return "\n".join(lignes)


def extraire_corps(tex):
    """Renvoie le contenu entre \\begin{document} et \\end{document}."""
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", tex, re.S)
    return m.group(1) if m else tex


def retirer_bibliographie(tex):
    tex = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "", tex, flags=re.S)
    tex = re.sub(r"\\bibliography\{[^}]*\}", "", tex)
    return tex


def retirer_floats(tex):
    """Jette le contenu brut des figures/tableaux, ne garde que la legende."""
    def repl(m):
        legendes = _RE_CAPTION.findall(m.group(2))
        return ("\n\n".join(l.strip() for l in legendes) + "\n\n") if legendes else ""
    return _RE_FLOAT.sub(repl, tex)


def gerer_listes(tex):
    """itemize/enumerate/description : garde le texte de chaque \\item, retire les balises."""
    tex = _RE_ITEM.sub("\n\n", tex)
    for env in ("itemize", "enumerate", "description"):
        tex = re.sub(r"\\begin\{" + env + r"\}(\[[^\]]*\])?", "", tex)
        tex = re.sub(r"\\end\{" + env + r"\}", "", tex)
    return tex


def nettoyer_fragment(texte):
    """Nettoyage generique applique a un fragment de texte (corps de section ou titre)."""
    # les equations inline ($...$) sont gardees telles quelles : on les met de cote
    # pendant le nettoyage pour que les commandes LaTeX qu'elles contiennent ne soient pas touchees.
    texte = _RE_MATH_DOUBLE_DOLLAR.sub(" [EQ] ", texte)
    texte = _RE_MATH_ENV.sub(" [EQ] ", texte)
    texte = _RE_MATH_BRACKETS.sub(" [EQ] ", texte)

    maths = []

    def _mettre_de_cote(m):
        maths.append(m.group(0))
        return f"\x00M{len(maths) - 1}\x00"

    texte = _RE_MATH_INLINE.sub(_mettre_de_cote, texte)

    for c in _COMMANDES_SANS_ARG:
        texte = re.sub(r"\\" + c + r"\b", "", texte)
    texte = re.sub(r"\\includegraphics(\[[^\]]*\])?\{[^}]*\}", "", texte)
    for c in _COMMANDES_ARG_SANS_TEXTE:
        texte = re.sub(r"\\" + c + r"\{[^}]*\}", "", texte)
    for c in ("hspace", "vspace"):
        texte = re.sub(r"\\" + c + r"\*?\{[^}]*\}", "", texte)
    texte = re.sub(r"\\setlength\{[^}]*\}\{[^}]*\}", "", texte)
    texte = re.sub(r"\\(setcounter|addcontentsline)\{[^}]*\}(\{[^}]*\})*", "", texte)
    texte = re.sub(r"\\(newcommand|renewcommand)\{?\\?[a-zA-Z]+\}?(\[[0-9]+\])?\{(?:[^{}]|\{[^{}]*\})*\}", "", texte)
    # note de bas de page : texte garde, entoure d'espaces pour ne pas coller aux mots voisins
    texte = _RE_FOOTNOTE.sub(lambda m: " " + m.group(1) + " ", texte)

    # environnements restants (equation, align, abstract, quote...) : garder le contenu
    texte = re.sub(r"\\begin\{[a-zA-Z*]+\}(\[[^\]]*\])?", "", texte)
    texte = re.sub(r"\\end\{[a-zA-Z*]+\}", "", texte)

    for mot, rempl in _SYMBOLES.items():
        texte = texte.replace(mot, rempl)

    texte = _RE_ACCENT.sub(lambda m: m.group(1), texte)
    for _ in range(3):  # commandes de mise en forme imbriquees (\textbf{\emph{...}})
        nouveau = _RE_BRACE_CMD.sub(lambda m: m.group(1), texte)
        if nouveau == texte:
            break
        texte = nouveau
    texte = _RE_BARE_CMD.sub("", texte)
    texte = texte.replace("{", "").replace("}", "")

    for echappe, car in _ESCAPES.items():
        texte = texte.replace(echappe, car)

    texte = re.sub(r"[ \t]+", " ", texte)
    texte = re.sub(r"\n[ \t]*\n+", "\n\n", texte)

    for i, m in enumerate(maths):
        texte = texte.replace(f"\x00M{i}\x00", m)
    return texte.strip()


def extraire_sections(tex):
    """Decoupe le texte en (titre_section, texte) dans l'ordre du document."""
    matches = list(_RE_SECTION.finditer(tex))
    if not matches:
        return [("", nettoyer_fragment(tex))]
    sections = []
    if matches[0].start() > 0:
        sections.append(("", nettoyer_fragment(tex[:matches[0].start()])))
    for idx, m in enumerate(matches):
        titre = nettoyer_fragment(m.group(2))
        debut = m.end()
        fin = matches[idx + 1].start() if idx + 1 < len(matches) else len(tex)
        sections.append((titre, nettoyer_fragment(tex[debut:fin])))
    return sections


def extraire_texte(tex_brut):
    """Pipeline complet : .tex brut -> liste [(titre_section, texte_nettoye), ...]."""
    tex = strip_comments(tex_brut)
    tex = extraire_corps(tex)
    tex = retirer_bibliographie(tex)
    tex = retirer_floats(tex)
    tex = _RE_LABEL.sub("", tex)
    tex = _RE_CITE.sub(" [CIT] ", tex)
    tex = _RE_REF.sub(" [CIT] ", tex)
    tex = gerer_listes(tex)
    return extraire_sections(tex)


def decouper_en_chunks(mots, max_mots=MAX_MOTS, recouvrement=RECOUVREMENT):
    """Fenetre glissante sur une liste de mots : max_mots par chunk, recouvrement en %."""
    if not mots:
        return []
    pas = max(1, int(max_mots * (1 - recouvrement)))
    chunks, i, n = [], 0, len(mots)
    while i < n:
        chunks.append(mots[i:i + max_mots])
        if i + max_mots >= n:
            break
        i += pas
    return chunks


def chunks_article(domaine, doc_id, tex_dir):
    """Construit les chunks d'un article : [{chunk_id, doc_id, domain, section_title, chunk_index, text}, ...]."""
    main = find_main(tex_dir)
    if main is None:
        print(f"  [{domaine}/{doc_id}] aucun fichier .tex principal, article ignore")
        return []
    tex_brut = main.read_text(encoding="utf-8", errors="replace")
    sections = extraire_texte(tex_brut)

    resultats, idx = [], 0
    for titre, texte in sections:
        mots = texte.split()
        for groupe in decouper_en_chunks(mots):
            resultats.append({
                "chunk_id": f"{doc_id}_{idx:04d}",
                "doc_id": doc_id,
                "domain": domaine,
                "section_title": titre,
                "chunk_index": idx,
                "text": " ".join(groupe),
            })
            idx += 1
    return resultats


def lister_articles(data, domaines, ids, limit=None):
    for dom in domaines:
        dom_dir = data / "tex" / dom
        if not dom_dir.is_dir():
            continue
        n = 0
        for art_dir in sorted(p for p in dom_dir.iterdir() if p.is_dir()):
            if ids and art_dir.name not in ids:
                continue
            if limit is not None and n >= limit:
                break
            n += 1
            yield dom, art_dir.name, art_dir


def calculer_embeddings(textes, batch_size):
    """Encode les textes avec E5 (prefixe passage), par lots. Renvoie un tableau numpy ou None."""
    try:
        import numpy as np  # noqa: F401
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print(
            "\nsentence-transformers (et/ou numpy) n'est pas installe : les embeddings ne sont pas calcules.\n"
            "chunks.jsonl a tout de meme ete ecrit.\n"
            "Pour activer cette etape, installe (apres ton accord) :\n"
            "  uv add --group video sentence-transformers numpy   (depuis backend/, deja prevu pour le module video)\n"
            "  ou : pip install sentence-transformers numpy       (dans l'environnement de data_latex)\n"
            "Puis relance ce script.\n"
        )
        return None

    modele = SentenceTransformer(MODELE_E5)
    vecteurs = modele.encode(
        [PREFIXE_E5 + t for t in textes],
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return vecteurs


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("data", type=Path, help="dossier data_latex/data")
    p.add_argument("--domains", nargs="*", default=list(DOMAINS), help="sous-ensemble de domaines")
    p.add_argument("--ids", nargs="*", default=None, help="restreindre a ces identifiants arXiv")
    p.add_argument("--limit", type=int, default=None, help="limiter a N articles par domaine (test rapide)")
    p.add_argument("--no-embed", action="store_true", help="ne pas calculer les embeddings")
    p.add_argument("--batch-size", type=int, default=32)
    args = p.parse_args()

    ids = set(args.ids) if args.ids else None
    tous_chunks = []
    for dom, doc_id, tex_dir in lister_articles(args.data, args.domains, ids, args.limit):
        chunks = chunks_article(dom, doc_id, tex_dir)
        tous_chunks.extend(chunks)
        print(f"{dom}/{doc_id} : {len(chunks)} chunks")

    out_dir = args.data / "index"
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = out_dir / "chunks.jsonl"
    with open(chunks_path, "w", encoding="utf-8") as f:
        for c in tous_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"\n{len(tous_chunks)} chunks -> {chunks_path}")

    if args.no_embed or not tous_chunks:
        return

    vecteurs = calculer_embeddings([c["text"] for c in tous_chunks], args.batch_size)
    if vecteurs is None:
        return
    emb_path = out_dir / "chunks_embeddings.npy"
    import numpy as np
    np.save(emb_path, vecteurs)
    print(f"{vecteurs.shape[0]} embeddings ({vecteurs.shape[1]} dim) -> {emb_path}")


if __name__ == "__main__":
    main()
