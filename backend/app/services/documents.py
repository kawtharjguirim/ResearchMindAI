"""
Documents importés : PDF (texte par page).

La vérification du type se fait sur le contenu du fichier (en-tête), pas sur l'extension.
Un PDF scanné sans couche de texte ne contient rien à lire : un OCR reste à faire.
"""
from pathlib import Path

from pypdf import PdfReader

from app.services.video.config import STORAGE_DIR
from app.services.web import decouper

DOCUMENTS_DIR = STORAGE_DIR / "documents"
TAILLE_MAX_PDF = 50 * 1024**2     # 50 Mo
EN_TETE_PDF = b"%PDF-"


class DocumentError(Exception):
    """Document inutilisable. Le message est affiché tel quel à l'utilisateur."""


def est_pdf(entete: bytes) -> bool:
    """Vrai si les premiers octets du fichier sont ceux d'un PDF."""
    return entete.startswith(EN_TETE_PDF)


def lire_pages(chemin: Path) -> list[tuple[int, str]]:
    """(numéro de page, texte) pour chaque page qui contient du texte."""
    try:
        lecteur = PdfReader(str(chemin))
        if lecteur.is_encrypted:
            lecteur.decrypt("")   # PDF protégé sans mot de passe utilisateur
    except Exception as e:  # noqa: BLE001 : pypdf lève des exceptions variées sur un fichier abîmé
        raise DocumentError("Unreadable PDF, or it is protected by a password.") from e

    pages = []
    for numero, page in enumerate(lecteur.pages, start=1):
        texte = (page.extract_text() or "").strip()
        if texte:
            pages.append((numero, texte))
    return pages


def decouper_pages(pages: list[tuple[int, str]]) -> list[dict]:
    """Passages de 200 mots au plus, chacun étiqueté avec sa page (« p. 3 »)."""
    passages = []
    for numero, texte in pages:
        for morceau in decouper(texte):
            passages.append({"start": 0.0, "end": 0.0, "timestamp": f"p. {numero}", "text": morceau["text"]})
    return passages
