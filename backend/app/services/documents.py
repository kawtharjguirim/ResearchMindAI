"""
Documents importés : PDF (texte par page) et images (texte reconnu par OCR).

La vérification du type se fait sur le contenu du fichier (en-tête), pas sur l'extension.
Un PDF scanné sans couche de texte ne contient rien à lire : l'image de chaque page n'est pas
analysée (un OCR par page reste à faire).
"""
import os
import re
from pathlib import Path

from pypdf import PdfReader

from app.services.video.config import STORAGE_DIR
from app.services.web import decouper

DOCUMENTS_DIR = STORAGE_DIR / "documents"
TAILLE_MAX_PDF = 50 * 1024**2      # 50 Mo
TAILLE_MAX_IMAGE = 15 * 1024**2    # 15 Mo
EN_TETE_PDF = b"%PDF-"
EN_TETE_PNG = b"\x89PNG\r\n\x1a\n"
EN_TETE_JPEG = b"\xff\xd8\xff"
MOTS_PAR_PASSAGE_PDF = 100   # plus court qu'une page web : un résumé ou un paragraphe reste un passage à part

_ocr = None  # moteur OCR, chargé au premier usage


class DocumentError(Exception):
    """Document inutilisable. Le message est affiché tel quel à l'utilisateur."""


def est_pdf(entete: bytes) -> bool:
    """Vrai si les premiers octets du fichier sont ceux d'un PDF."""
    return entete.startswith(EN_TETE_PDF)


def est_image(entete: bytes) -> bool:
    """Vrai si les premiers octets sont ceux d'un PNG ou d'un JPEG."""
    return entete.startswith(EN_TETE_PNG) or entete.startswith(EN_TETE_JPEG)


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


def _ligne_utile(ligne: str) -> bool:
    """Écarte les lignes parasites : numéros de page, puces ou symboles isolés (moins de deux caractères alphanumériques)."""
    return sum(c.isalnum() for c in ligne) >= 2


_MARQUES_REFERENCE = re.compile(r"\[\d+\]|\[\d{4}\.\d+\]|\bet al\.")
_ANNEES = re.compile(r"\b(?:19|20)\d{2}\b")


def est_bibliographie(texte: str) -> bool:
    """Vrai si le passage ressemble à une bibliographie : marques [n], « et al. » ou plusieurs années."""
    marques = len(_MARQUES_REFERENCE.findall(texte))
    annees = len(_ANNEES.findall(texte))
    return marques >= 2 or (marques >= 1 and annees >= 2)


def extraire_resume(pages: list[tuple[int, str]]) -> dict | None:
    """Passage « titre + résumé » d'un article scientifique, repéré à la section « Abstract »."""
    for numero, texte in pages:
        m = re.search(r"\bAbstract\b\.?", texte)
        if not m:
            continue
        suite = texte[m.end():]
        fin = re.search(r"\n\s*(?:1\.?\s*)?Introduction\b", suite, re.IGNORECASE)
        resume = suite[: fin.start()] if fin else suite[:1500]
        titre = pages[0][1].split("\n")[:3] if pages else []
        contenu = " ".join(" ".join(titre).split()) + "\n" + " ".join(resume.split())
        # Étiquette « (abstract) » : repère le résumé pour le garder dans les passages de réponse.
        return {"start": 0.0, "end": 0.0, "timestamp": f"p. {numero} (abstract)", "text": contenu.strip()}
    return None


def decouper_pages(pages: list[tuple[int, str]], max_mots: int = MOTS_PAR_PASSAGE_PDF) -> list[dict]:
    """Passages de max_mots mots au plus, chacun étiqueté avec sa page (« p. 3 »).

    Si l'article a un résumé, il devient le premier passage, pour répondre à « de quoi parle ce document ».
    """
    passages = []
    resume = extraire_resume(pages)
    if resume and len(resume["text"].split()) >= 20:
        passages.append(resume)
    for numero, texte in pages:
        propre = "\n".join(ligne for ligne in texte.split("\n") if _ligne_utile(ligne))
        if not propre:
            continue
        for morceau in decouper(propre, max_mots=max_mots):
            passages.append({"start": 0.0, "end": 0.0, "timestamp": f"p. {numero}", "text": morceau["text"]})
    return passages


def _moteur_ocr():
    """Moteur PaddleOCR, chargé au premier usage (il est lourd)."""
    global _ocr
    if _ocr is None:
        # Sous Windows, torch doit être chargé avant paddle : sinon leurs DLL entrent en conflit.
        import torch  # noqa: F401
        # Pas de vérification de connexion aux serveurs de modèles à chaque lancement.
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        # oneDNN (MKLDNN) plante avec paddle 3.3 sous Windows : on le désactive.
        _ocr = PaddleOCR(lang="fr", enable_mkldnn=False)
    return _ocr


def lire_texte_image(chemin: Path) -> list[str]:
    """Étiquettes reconnues dans une image (PaddleOCR), une par zone de texte. Liste vide si l'image n'a pas de texte."""
    try:
        resultats = _moteur_ocr().predict(str(chemin))
    except Exception as e:  # noqa: BLE001 : image illisible ou moteur indisponible
        raise DocumentError("Unreadable image.") from e
    return [texte.strip() for resultat in resultats for texte in resultat["rec_texts"] if texte.strip()]


def decouper_image(etiquettes: list[str]) -> list[dict]:
    """Un passage par étiquette, étiqueté « image » (pas de page ni de seconde).

    Les étiquettes parasites sont écartées : moins de deux caractères alphanumériques (« . », « + », « | »…).
    """
    utiles = [e for e in etiquettes if sum(c.isalnum() for c in e) >= 2]
    return [{"start": 0.0, "end": 0.0, "timestamp": "image", "text": etiquette} for etiquette in utiles]
