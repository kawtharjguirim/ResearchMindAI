"""
Pages web : téléchargement sécurisé, texte principal et découpage en passages.

Sécurité : seules les adresses publiques en http(s) sont acceptées. Chaque adresse, y compris
chaque redirection, est vérifiée avant d'être demandée, pour qu'un lien ne puisse pas lire le
réseau interne du serveur (localhost, 192.168.x.x, métadonnées cloud, etc.).
"""
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

TAILLE_MAX = 2 * 1024**2     # 2 Mo de HTML
DELAI = 15.0                 # secondes
MAX_REDIRECTIONS = 5
MAX_MOTS = 200               # taille cible d'un passage, comme pour les vidéos


class WebError(Exception):
    """Page inutilisable. Le message est affiché tel quel à l'utilisateur."""


def verifier_url(url: str) -> str:
    """Lève WebError si l'adresse n'est pas une adresse web publique."""
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise WebError("Invalid link: only http:// and https:// addresses are accepted.")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or None)
    except socket.gaierror as e:
        raise WebError("Address not found (check the link).") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise WebError("Non-public address: this link cannot be imported.")
    return url


def telecharger_html(url: str) -> tuple[str, str]:
    """(adresse finale après redirections, HTML de la page)."""
    courante = verifier_url(url)
    with httpx.Client(timeout=DELAI, follow_redirects=False,
                      headers={"User-Agent": "ResearchMindAI/1.0"}) as client:
        for _ in range(MAX_REDIRECTIONS + 1):
            with client.stream("GET", courante) as r:
                if r.is_redirect:
                    courante = verifier_url(urljoin(courante, r.headers.get("location", "")))
                    continue
                if r.status_code >= 400:
                    raise WebError(f"The page returned an error ({r.status_code}).")
                if "text/html" not in r.headers.get("content-type", ""):
                    raise WebError("This address does not point to an HTML page.")
                octets = bytearray()
                for bloc in r.iter_bytes():
                    octets += bloc
                    if len(octets) > TAILLE_MAX:
                        raise WebError("Page too large (over 2 MB).")
                return courante, bytes(octets).decode(r.encoding or "utf-8", errors="replace")
    raise WebError("Too many redirects.")


def extraire_texte(html: str, url: str) -> tuple[str, str]:
    """(titre, texte principal de la page, un paragraphe par ligne)."""
    texte = trafilatura.extract(html, url=url, include_comments=False, include_tables=False,
                                output_format="txt") or ""
    meta = trafilatura.extract_metadata(html)
    titre = (meta.title or "").strip() if meta else ""
    return titre, texte


def decouper(texte: str, max_mots: int = MAX_MOTS) -> list[dict]:
    """Passages regroupant des paragraphes entiers, jusqu'à max_mots mots.

    Une page n'a pas d'horodatage : start et end valent 0, et le champ timestamp porte le numéro
    du passage (« § 3 »), affiché dans l'interface à la place d'une seconde.
    """
    paragraphes = [p.strip() for p in texte.split("\n") if p.strip()]
    groupes: list[list[str]] = []
    courant: list[str] = []
    mots = 0
    for p in paragraphes:
        n = len(p.split())
        if courant and mots + n > max_mots:
            groupes.append(courant)
            courant, mots = [], 0
        courant.append(p)
        mots += n
    if courant:
        groupes.append(courant)
    return [{"start": 0.0, "end": 0.0, "timestamp": f"§ {i + 1}", "text": "\n".join(g)}
            for i, g in enumerate(groupes)]
