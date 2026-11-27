"""
Sources (module « capsule vidéo ») : import d'une vidéo, suivi de son traitement, suppression.

L'import envoie les octets de la vidéo directement dans le corps de la requête
(pas de formulaire multipart : évite la dépendance python-multipart) :

    POST /sources/video?filename=cours.mp4&title=Cours%201&language=fr
    Content-Type: video/mp4
    <octets de la vidéo>

Le traitement (transcription, découpage, embeddings) tourne en tâche de fond ;
le client suit l'avancement avec GET /sources/{id} (champ `status`).
"""
import os
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.core.media_token import sign_play_token, verify_play_token
from app.db.session import get_db
from app.models.project import Project
from app.models.source import Chunk, Source, SourceStatus, SourceType
from app.schemas.source import PlayLink, SourceRead, TranscriptChunk, UrlSourceCreate
from app.services import papers
from app.services.video import pipeline
from app.services.video.config import EXT_VIDEO, TAILLE_MAX_VIDEO, VIDEOS_DIR
from app.services.video.youtube import extraire_id
from app.services.web import WebError, verifier_url
from app.services.documents import DOCUMENTS_DIR, TAILLE_MAX_PDF, est_pdf

router = APIRouter(prefix="/sources", tags=["sources"])


def to_read(s: Source, chunk_count: int) -> SourceRead:
    return SourceRead(
        id=s.id, project_id=s.project_id, source_type=s.source_type, title=s.title, url=s.url,
        language=s.language, duration=s.duration, status=s.status, error=s.error,
        chunk_count=chunk_count, created_at=s.created_at, updated_at=s.updated_at,
    )


def _count(db: Session, source_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Chunk).where(Chunk.source_id == source_id)) or 0


def get_owned_source(db: Session, source_id: str, user: CurrentUser) -> Source:
    source = db.scalar(select(Source).where(Source.id == source_id, Source.user_id == user.id))
    if source is None:
        # 404 (not 403) so a user cannot probe for other users' source ids.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


def require_video_dependencies() -> None:
    manquantes = pipeline.dependances_manquantes()
    if manquantes:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Video module not installed (missing: {', '.join(manquantes)}). "
                   "Run 'uv sync --group video'.",
        )


@router.post("/video", response_model=SourceRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    request: Request,
    background: BackgroundTasks,
    filename: str = Query(min_length=1, max_length=300),
    title: str | None = Query(default=None, max_length=300),
    language: str | None = Query(default="fr", max_length=8),
    project_id: str | None = None,
    url: str = Query(default="", max_length=1000),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_video_dependencies()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in EXT_VIDEO:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"Unsupported video format. Allowed: {', '.join(EXT_VIDEO)}")
    if project_id and db.scalar(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    source_id = str(uuid.uuid4())
    stored = f"{source_id}{ext}"
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    path = VIDEOS_DIR / stored
    size = 0
    try:
        with open(path, "wb") as f:
            async for block in request.stream():
                size += len(block)
                if size > TAILLE_MAX_VIDEO:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                        detail=f"Video larger than {TAILLE_MAX_VIDEO // 1024**2} MB")
                f.write(block)
        if size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request body")
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    clean_title = (title or "").strip() or os.path.splitext(os.path.basename(filename))[0]
    source = Source(id=source_id, user_id=user.id, project_id=project_id, title=clean_title[:300],
                    filename=stored, url=url.strip(), language=language or None)
    db.add(source)
    db.commit()
    db.refresh(source)
    background.add_task(pipeline.traiter_source, source.id)
    return to_read(source, 0)


@router.post("/url", response_model=SourceRead, status_code=status.HTTP_202_ACCEPTED)
def import_url(
    body: UrlSourceCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Importe un lien YouTube : ses sous-titres sont lus, puis indexés en tâche de fond."""
    if body.project_id and db.scalar(
        select(Project.id).where(Project.id == body.project_id, Project.user_id == user.id)
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    video_id = extraire_id(body.url)
    if video_id is not None:
        url, type_source = f"https://www.youtube.com/watch?v={video_id}", SourceType.video
        titre_defaut, traitement = f"YouTube {video_id}", pipeline.traiter_source_youtube
    else:
        try:
            url = verifier_url(body.url.strip())
        except WebError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        type_source, traitement = SourceType.web, pipeline.traiter_source_web
        titre_defaut = urlparse(url).hostname or url

    source = Source(
        id=str(uuid.uuid4()), user_id=user.id, project_id=body.project_id, source_type=type_source,
        title=((body.title or "").strip() or titre_defaut)[:300],
        filename="", url=url, language=body.language or None,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    background.add_task(traitement, source.id)
    return to_read(source, 0)


@router.post("/file", response_model=SourceRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    request: Request,
    background: BackgroundTasks,
    filename: str = Query(min_length=1, max_length=300),
    title: str | None = Query(default=None, max_length=300),
    language: str | None = Query(default="fr", max_length=8),
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Import d'un PDF : les octets sont envoyés dans le corps, comme pour une vidéo."""
    if os.path.splitext(filename)[1].lower() != ".pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="Only PDF files are accepted for now.")
    type_source = SourceType.pdf
    taille_max = TAILLE_MAX_PDF
    if project_id and db.scalar(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    source_id = str(uuid.uuid4())
    stored = f"{source_id}.pdf"
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCUMENTS_DIR / stored
    size = 0
    try:
        with open(path, "wb") as f:
            async for block in request.stream():
                size += len(block)
                if size > taille_max:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                        detail=f"File larger than {taille_max // 1024**2} MB")
                f.write(block)
        if size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request body")
        # Le contenu compte, pas l'extension : on vérifie l'en-tête du fichier.
        with open(path, "rb") as f:
            entete = f.read(8)
        valide = est_pdf(entete)
        if not valide:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                detail="The file content does not match its extension.")
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    clean_title = (title or "").strip() or os.path.splitext(os.path.basename(filename))[0]
    source = Source(id=source_id, user_id=user.id, project_id=project_id, source_type=type_source,
                    title=clean_title[:300], filename=stored, url="", language=language or None)
    db.add(source)
    db.commit()
    db.refresh(source)
    background.add_task(pipeline.traiter_source_document, source.id)
    return to_read(source, 0)


@router.get("", response_model=list[SourceRead])
def list_sources(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    counts = (select(Chunk.source_id, func.count().label("n")).group_by(Chunk.source_id).subquery())
    query = (select(Source, func.coalesce(counts.c.n, 0))
             .outerjoin(counts, counts.c.source_id == Source.id)
             .where(Source.user_id == user.id))
    if project_id:
        query = query.where(Source.project_id == project_id)
    rows = db.execute(query.order_by(Source.created_at.desc())).all()
    videos = [to_read(s, n) for s, n in rows]
    # Sources papier : corpus arXiv réel si rag/ est disponible (app.services.papers), sinon
    # simulées. Elles n'appartiennent à aucun projet : exclues dès qu'un project_id est demandé.
    paper_sources = [] if project_id else [SourceRead(**p) for p in papers.list_sources()]
    return videos + paper_sources


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    source = get_owned_source(db, source_id, user)
    return to_read(source, _count(db, source.id))


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    source = get_owned_source(db, source_id, user)
    path = pipeline.chemin_video(source) if source.filename else None
    db.delete(source)
    db.commit()
    pipeline.oublier(source_id)
    if path is not None:
        path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{source_id}/transcript", response_model=list[TranscriptChunk])
def get_transcript(source_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    """Transcription découpée en passages, pour l'afficher en synchronisation avec le lecteur."""
    source = get_owned_source(db, source_id, user)
    chunks = db.scalars(select(Chunk).where(Chunk.source_id == source.id).order_by(Chunk.position)).all()
    return [TranscriptChunk(chunk_id=c.id, start=c.start, end=c.end, timestamp=c.timestamp, text=c.text)
            for c in chunks]


@router.get("/{source_id}/play-link", response_model=PlayLink)
def play_link(
    source_id: str,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Lien de lecture signé, valable 10 minutes : GET /sources/{id}/file?token=..."""
    source = get_owned_source(db, source_id, user)
    if source.status != SourceStatus.ready or not source.filename:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Video is not ready")
    token, expires_at = sign_play_token(source.id, user.id, settings)
    return PlayLink(url=f"{settings.api_prefix}/sources/{source_id}/file?token={token}", expires_at=expires_at)


@router.get("/{source_id}/file")
def play_file(
    source_id: str,
    token: str,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
):
    """Octets de la vidéo, protégés par le jeton signé (pas de Bearer : <video> ne l'envoie pas)."""
    verify_play_token(token, source_id, settings)
    source = db.get(Source, source_id)
    if source is None or not source.filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    path = pipeline.chemin_video(source)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing on disk")
    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "video/mp4"
    return FileResponse(path, media_type=media_type)
