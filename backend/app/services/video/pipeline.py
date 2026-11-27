"""
Orchestration côté application : traitement d'une source vidéo (transcription -> chunks ->
embeddings -> base) et questions-réponses sur une source prête.

Les routes n'appellent que ce module ; il fait le lien entre les tables Source/Chunk et les
services purs (transcription, chunking, search, qa).
"""
import importlib.util
import threading
from collections import OrderedDict
from urllib.parse import urlparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.source import Chunk, Source, SourceStatus, SourceType

from .chunking import construire_chunks
from .config import (DEPENDANCES, PLANCHER_RERANK_PDF, PLANCHER_RERANK_WEB, SEUIL_RERANK_PDF, SEUIL_RERANK_WEB,
                     VIDEOS_DIR)
from .qa import VideoQA
from .search import Index, encoder_passages
from .transcription import transcrire
from .youtube import YouTubeError, extraire_id, recuperer_segments
from app.services.web import WebError, decouper, extraire_texte, telecharger_html
from app.services.documents import (
    DOCUMENTS_DIR,
    DocumentError,
    est_bibliographie,
    decouper_image,
    decouper_pages,
    lire_pages,
    lire_texte_image,
)


def dependances_manquantes() -> list[str]:
    """Paquets du groupe « video » non installés (liste vide si tout est là)."""
    return [d for d in DEPENDANCES if importlib.util.find_spec(d) is None]


def chemin_video(source: Source):
    """Fichier stocké de la source : une vidéo, ou un PDF dans son propre dossier."""
    if source.source_type in (SourceType.pdf, SourceType.figure):
        return DOCUMENTS_DIR / source.filename
    return VIDEOS_DIR / source.filename


# ---------- Traitement d'une vidéo (tâche de fond) ----------

def _chunks_video(source: Source) -> list[dict]:
    """Passages d'une vidéo (ou d'un lien YouTube) à partir de ses segments horodatés."""
    chunks = construire_chunks(source.segments, source=source.url or source.title,
                               titre=source.title, langue=source.language, doc_id=source.id)
    if not chunks:
        raise ValueError("No speech detected in this video.")
    return chunks


def _indexer(db, source: Source, chunks: list[dict]) -> None:
    """Calcule les embeddings des passages, les enregistre et marque la source prête."""
    if not chunks:
        raise ValueError("No passage to index.")
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
            attendue = isinstance(erreur, (YouTubeError, WebError, DocumentError))
            texte = str(erreur) if attendue else f"{type(erreur).__name__}: {erreur}"
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
            _indexer(db, source, _chunks_video(source))
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
                raise YouTubeError("Invalid YouTube link.")
            segments, langue = recuperer_segments(video_id, source.language)
            source.language = langue
            source.duration = segments[-1]["end"]
            source.segments = segments
            source.status = SourceStatus.indexing
            db.commit()
            _indexer(db, source, _chunks_video(source))
        except Exception as e:  # noqa: BLE001 : l'erreur est stockée et affichée dans l'interface
            db.rollback()
            _echouer(source_id, e)


def traiter_source_web(source_id: str) -> None:
    """Télécharge une page web, en extrait le texte principal et l'indexe. Ne lève jamais."""
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if source is None:
            return
        try:
            source.status, source.error = SourceStatus.transcribing, ""
            db.commit()
            adresse, html = telecharger_html(source.url)
            titre, texte = extraire_texte(html, adresse)
            chunks = decouper(texte)
            if not chunks:
                raise WebError("No readable text on this page.")
            source.url = adresse
            # Titre par défaut (nom de domaine) : on le remplace par le titre de la page.
            if titre and source.title == (urlparse(adresse).hostname or ""):
                source.title = titre[:300]
            source.status = SourceStatus.indexing
            db.commit()
            _indexer(db, source, chunks)
        except Exception as e:  # noqa: BLE001 : l'erreur est stockée et affichée dans l'interface
            db.rollback()
            _echouer(source_id, e)


def traiter_source_document(source_id: str) -> None:
    """Lit un PDF (texte par page) ou une image (OCR), puis l'indexe. Ne lève jamais."""
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if source is None:
            return
        try:
            source.status, source.error = SourceStatus.transcribing, ""
            db.commit()
            if source.source_type == SourceType.figure:
                chunks = decouper_image(lire_texte_image(chemin_video(source)))
            else:
                chunks = decouper_pages(lire_pages(chemin_video(source)))
            if not chunks:
                raise DocumentError("No readable text found. Scanned pages need OCR, which is not available yet.")
            source.status = SourceStatus.indexing
            db.commit()
            _indexer(db, source, chunks)
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
    # Pages web et images : seuils web. PDF : seuils plus bas, car leurs scores sont plus faibles.
    if source.source_type == SourceType.pdf:
        resume = [c.as_search_chunk() for c in chunks if c.timestamp.endswith("(abstract)")][:1]
        seuils = {"seuil_rerank": SEUIL_RERANK_PDF, "plancher_rerank": PLANCHER_RERANK_PDF,
                  "ecarter": est_bibliographie,   # pas de réponse tirée de la bibliographie
                  "toujours": resume}             # le résumé de l'article reste disponible
    elif source.source_type in (SourceType.web, SourceType.figure):
        seuils = {"seuil_rerank": SEUIL_RERANK_WEB, "plancher_rerank": PLANCHER_RERANK_WEB}
    else:
        seuils = {}
    qa = VideoQA(index_pour(source, list(chunks)), segments=source.segments, langue_video=source.language,
                 **seuils)
    return qa.repondre(question)
