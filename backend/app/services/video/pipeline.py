"""
Orchestration côté application : traitement d'une source vidéo (transcription -> chunks ->
embeddings -> base) et questions-réponses sur une source prête.

Les routes n'appellent que ce module ; il fait le lien entre les tables Source/Chunk et les
services purs (transcription, chunking, search, qa).
"""
import importlib.util
import threading
from collections import OrderedDict

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.source import Chunk, Source, SourceStatus

from .chunking import construire_chunks
from .config import DEPENDANCES, VIDEOS_DIR
from .qa import VideoQA
from .search import Index, encoder_passages
from .transcription import transcrire
from .youtube import YouTubeError, extraire_id, recuperer_segments


def dependances_manquantes() -> list[str]:
    """Paquets du groupe « video » non installés (liste vide si tout est là)."""
    return [d for d in DEPENDANCES if importlib.util.find_spec(d) is None]


def chemin_video(source: Source):
    return VIDEOS_DIR / source.filename


# ---------- Traitement d'une vidéo (tâche de fond) ----------

def _indexer(db, source: Source) -> None:
    """Découpe les segments de la source en passages, calcule leurs embeddings et marque la source prête."""
    chunks = construire_chunks(source.segments, source=source.url or source.title,
                               titre=source.title, langue=source.language, doc_id=source.id)
    if not chunks:
        raise ValueError("Aucune parole détectée dans la vidéo.")
    vecteurs = encoder_passages([c["text"] for c in chunks])
    source.chunks = [Chunk(position=i, start=c["start"], end=c["end"], timestamp=c["timestamp"],
                           text=c["text"], embedding=[float(x) for x in v])
                     for i, (c, v) in enumerate(zip(chunks, vecteurs))]
    source.status = SourceStatus.ready
    db.commit()


def _echouer(source_id: str, erreur: Exception) -> None:
    """Enregistre l'erreur de traitement sur la source, pour l'afficher dans l'interface."""
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if source is not None:
            # Une erreur attendue (lien sans sous-titres, par exemple) s'affiche sans préfixe technique.
            texte = str(erreur) if isinstance(erreur, YouTubeError) else f"{type(erreur).__name__}: {erreur}"
            source.status, source.error = SourceStatus.error, texte[:2000]
            db.commit()


def traiter_source(source_id: str) -> None:
    """Transcrit, découpe et indexe une source. Met à jour son statut ; ne lève jamais."""
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if source is None:
            return
        try:
            source.status, source.error = SourceStatus.transcribing, ""
            db.commit()
            t = transcrire(str(chemin_video(source)), source.language)
            source.language, source.duration, source.segments = t["language"], t["duration"], t["segments"]
            source.status = SourceStatus.indexing
            db.commit()
            _indexer(db, source)
        except Exception as e:  # noqa: BLE001 : l'erreur est stockée et affichée dans l'interface
            db.rollback()
            _echouer(source_id, e)


def traiter_source_youtube(source_id: str) -> None:
    """Récupère les sous-titres d'un lien YouTube, puis les indexe comme une vidéo. Ne lève jamais."""
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if source is None:
            return
        try:
            source.status, source.error = SourceStatus.transcribing, ""
            db.commit()
            video_id = extraire_id(source.url)
            if video_id is None:
                raise YouTubeError("Lien YouTube invalide.")
            segments, langue = recuperer_segments(video_id, source.language)
            source.language = langue
            source.duration = segments[-1]["end"]
            source.segments = segments
            source.status = SourceStatus.indexing
            db.commit()
            _indexer(db, source)
        except Exception as e:  # noqa: BLE001 : l'erreur est stockée et affichée dans l'interface
            db.rollback()
            _echouer(source_id, e)


# ---------- Questions-réponses ----------

_CACHE_MAX = 4                     # index gardés en mémoire (un par vidéo)
_cache: "OrderedDict[tuple, Index]" = OrderedDict()
_verrou = threading.Lock()


def index_pour(source: Source, chunks: list[Chunk]) -> Index:
    """Index de recherche d'une source, reconstruit depuis la base et gardé en cache."""
    cle = (source.id, source.updated_at)
    with _verrou:
        if cle in _cache:
            _cache.move_to_end(cle)
            return _cache[cle]
    embeddings = [c.embedding for c in chunks]
    index = Index([c.as_search_chunk() for c in chunks],
                  embeddings=embeddings if all(e is not None for e in embeddings) else None)
    if getattr(index, "embeddings_recalcules", False):
        _enregistrer_embeddings(source.id, index.emb)
    with _verrou:
        _cache[cle] = index
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    return index


def _enregistrer_embeddings(source_id: str, vecteurs) -> None:
    """Stocke les vecteurs recalculés (changement de modèle) pour ne pas les recalculer au redémarrage."""
    with SessionLocal() as db:
        chunks = db.scalars(select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.position)).all()
        if len(chunks) != len(vecteurs):
            return
        for c, v in zip(chunks, vecteurs):
            c.embedding = [float(x) for x in v]
        db.commit()


def oublier(source_id: str) -> None:
    """Retire du cache les index d'une source (après suppression)."""
    with _verrou:
        for cle in [k for k in _cache if k[0] == source_id]:
            del _cache[cle]


def repondre(db, source: Source, question: str) -> dict:
    chunks = db.scalars(select(Chunk).where(Chunk.source_id == source.id).order_by(Chunk.position)).all()
    qa = VideoQA(index_pour(source, list(chunks)), segments=source.segments, langue_video=source.language)
    return qa.repondre(question)
