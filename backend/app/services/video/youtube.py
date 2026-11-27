"""
Sous-titres YouTube : identifiant de la vidéo et segments horodatés.

On ne télécharge pas la vidéo : on lit les sous-titres publics (manuels ou automatiques)
fournis par YouTube. Les segments ont la même forme que ceux de faster-whisper
({start, end, text}), donc la suite de la pipeline (découpage, embeddings) est identique.
"""
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

_ID_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOTES_YOUTUBE = {"youtube.com", "m.youtube.com", "music.youtube.com"}


class YouTubeError(Exception):
    """Lien ou sous-titres inutilisables. Le message est affiché tel quel à l'utilisateur."""


def extraire_id(url: str) -> str | None:
    """Identifiant de 11 caractères d'un lien YouTube, ou None si le lien n'en est pas un."""
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parts = urlparse(url)
    hote = (parts.hostname or "").lower().removeprefix("www.")
    chemin = parts.path

    if hote == "youtu.be":
        candidat = chemin.strip("/").split("/")[0]
    elif hote in _HOTES_YOUTUBE:
        if chemin == "/watch":
            candidat = parse_qs(parts.query).get("v", [""])[0]
        elif chemin.startswith(("/shorts/", "/embed/", "/live/")):
            morceaux = chemin.split("/")
            candidat = morceaux[2] if len(morceaux) > 2 else ""
        else:
            return None
    else:
        return None

    return candidat if _ID_VIDEO.match(candidat) else None


def recuperer_segments(video_id: str, langue: str | None) -> tuple[list[dict], str]:
    """
    Segments [{start, end, text}] et code de langue des sous-titres obtenus.

    La langue demandée passe en premier, puis français et anglais. YouTube renvoie les
    sous-titres automatiques si aucun sous-titre manuel n'existe.
    """
    preferences = list(dict.fromkeys(l for l in (langue, "fr", "en") if l))
    try:
        transcription = YouTubeTranscriptApi().fetch(video_id, languages=preferences)
    except TranscriptsDisabled as e:
        raise YouTubeError("This video has no subtitles (they are disabled by the author).") from e
    except NoTranscriptFound as e:
        raise YouTubeError(f"No subtitles in {', '.join(preferences)} for this video.") from e
    except Exception as e:  # noqa: BLE001 : erreurs réseau ou YouTube, à présenter simplement
        raise YouTubeError(f"Could not read the subtitles ({type(e).__name__}).") from e

    segments = [
        {"start": float(s.start), "end": float(s.start) + float(s.duration), "text": s.text.strip()}
        for s in transcription
        if s.text.strip()
    ]
    if not segments:
        raise YouTubeError("The subtitles of this video are empty.")
    return segments, transcription.language_code
