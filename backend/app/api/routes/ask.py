"""
Questions-réponses sur une source vidéo prête (mode extractif, qwen2.5:3b via Ollama).

    POST /ask  {"source_id": "...", "question": "..."}

La réponse cite la phrase exacte de la transcription avec son horodatage, ou indique que
la vidéo ne contient pas la réponse (règle combinée : plancher 0,02, seuil 0,07).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.sources import get_owned_source, require_video_dependencies
from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.source import SourceStatus
from app.schemas.source import AskRequest, AskResponse, Citation, Passage
from app.services.video import pipeline
from app.services.video.llm import OllamaIndisponible

router = APIRouter(tags=["ask"])


def to_response(r: dict) -> AskResponse:
    c, rf = r.get("citation"), r.get("reformulation")
    return AskResponse(
        question=r["question"],
        status=r["statut"],
        answer=r["reponse"],
        citation=Citation(text=c["texte"], timestamp=c["timestamp"], passage=c["passage"]) if c else None,
        rephrasing=rf["texte"] if rf and rf["retenue"] and not rf["identique_a_la_citation"] else None,
        passages=[Passage(chunk_id=p["chunk"]["chunk_id"], timestamp=p["chunk"]["timestamp"],
                          start=p["chunk"]["start"], end=p["chunk"]["end"], text=p["chunk"]["text"],
                          rerank=round(p["rerank"], 4))
                  for p in r["passages"]],
        timings={k: round(v, 2) for k, v in r["temps"].items()},
    )


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    source = get_owned_source(db, body.source_id, user)
    if source.status != SourceStatus.ready:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Source is not ready (status: {source.status.value})")
    require_video_dependencies()
    try:
        return to_response(pipeline.repondre(db, source, body.question))
    except OllamaIndisponible as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
