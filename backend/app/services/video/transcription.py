"""Transcription d'une vidéo avec faster-whisper (repris de transcrire.py)."""
import glob
import os
import sys
from functools import lru_cache

from .config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL_DIR, WHISPER_PROMPT


def _rendre_dll_cuda_visibles() -> None:
    """Windows : ajoute les DLL CUDA installées par pip (paquets nvidia-*) au chemin de recherche."""
    if os.name != "nt":
        return
    for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]


@lru_cache(maxsize=1)
def charger_modele():
    """Charge le modèle Whisper une seule fois par processus."""
    if WHISPER_DEVICE == "cuda":
        _rendre_dll_cuda_visibles()
    from faster_whisper import WhisperModel

    return WhisperModel(WHISPER_MODEL_DIR, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)


def transcrire(chemin_video: str, langue: str | None = "fr", on_segment=None) -> dict:
    """
    Transcrit une vidéo. Renvoie {"source", "language", "duration", "segments": [{start, end, text}]}.
    on_segment(segment) est appelé à chaque segment (suivi de progression), facultatif.
    """
    segments, info = charger_modele().transcribe(
        chemin_video,
        language=langue,
        beam_size=1,              # plus rapide, qualité quasi identique
        initial_prompt=WHISPER_PROMPT,
        vad_filter=True,          # ignore les silences
    )
    liste = []
    for s in segments:
        seg = {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
        liste.append(seg)
        if on_segment:
            on_segment(seg)
    return {
        "source": os.path.basename(chemin_video),
        "language": info.language,
        "duration": round(info.duration, 2),
        "segments": liste,
    }
