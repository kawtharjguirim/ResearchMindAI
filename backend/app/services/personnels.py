"""
Documents personnels : Word (.docx), Markdown (.md) et texte brut (.txt).

Le PDF a son propre module (documents.py). Ici, le texte est lu en entier puis découpé en
passages de même taille que les pages web : un document personnel n'a ni pages ni horodatage.
"""
import zipfile
from pathlib import Path

from app.services.web import decouper

EXTENSIONS_PERSONNELLES = (".docx", ".md", ".txt")
EN_TETE_DOCX = b"PK\x03\x04"


class DocumentPersonnelError(Exception):
    """Document personnel inutilisable. Le message est affiché tel quel à l'utilisateur."""


def est_docx(chemin: Path) -> bool:
    """Un .docx est une archive zip qui contient word/document.xml."""
    try:
        with zipfile.ZipFile(chemin) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def est_texte(chemin: Path) -> bool:
    """Vrai si le fichier est du texte UTF-8 sans octet nul (les formats binaires sont refusés)."""
    try:
        contenu = chemin.read_bytes()
        contenu.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return b"\x00" not in contenu


def lire_texte_personnel(chemin: Path) -> str:
    """Texte complet d'un document personnel (.docx, .md ou .txt)."""
    if chemin.suffix.lower() == ".docx":
        try:
            from docx import Document
            document = Document(str(chemin))
        except Exception as e:  # noqa: BLE001 : fichier Word abîmé ou protégé
            raise DocumentPersonnelError("Unreadable Word file.") from e
        morceaux = [p.text for p in document.paragraphs]
        for tableau in document.tables:
            for ligne in tableau.rows:
                morceaux.append(" | ".join(cellule.text for cellule in ligne.cells))
        return "\n".join(m for m in morceaux if m.strip())
    try:
        return chemin.read_bytes().decode("utf-8")
    except UnicodeDecodeError as e:
        raise DocumentPersonnelError("Not a UTF-8 text file.") from e


def decouper_personnel(texte: str) -> list[dict]:
    """Passages de 100 mots au plus, étiquetés « § n » comme les pages web."""
    return decouper(texte, max_mots=100)
