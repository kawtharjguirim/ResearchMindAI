"""Outils de texte sans dépendance : normalisation, phrases, horodatage, couverture."""
import re
import unicodedata

MOTS_VIDES = set("""le la les un une des de du d l et ou en au aux a à ce ces cet cette
qui que quoi dont où il elle ils elles on je tu nous vous se sa son ses leur leurs
est sont été être avoir pas ne n y ça c s qu pour par sur dans avec plus mais
the a an of to and or in on is are was it that this for with as be""".split())


def normaliser(texte: str) -> list[str]:
    """Minuscules, sans accents, sans mots vides ni mots d'une lettre."""
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return [m for m in re.findall(r"\w+", texte) if m not in MOTS_VIDES and len(m) > 1]


def phrases(texte: str) -> list[str]:
    """Découpe un texte en phrases (sur . ! ? …)."""
    return [p.strip() for p in re.split(r"(?<=[.!?…])\s+", texte) if p.strip()]


def hms(secondes: float) -> str:
    s = int(secondes)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def couverture(phrase: str, texte: str) -> float:
    """Part des mots (normalisés) de la phrase présents dans le texte : 1.0 = recopiée."""
    mots = normaliser(phrase)
    vus = set(normaliser(texte))
    return sum(m in vus for m in mots) / len(mots) if mots else 0.0
