"""
Questions-réponses génériques, sur une source vidéo (mode extractif, qwen2.5:3b via Ollama)
ou sur une source papier simulée (app.services.papers, en attendant le contrat du corpus).

    POST /answer  {"source_id": "...", "question": "..."}  ->  {reponse, citations, verifie}

Pour une vidéo, la réponse cite la phrase exacte de la transcription avec son horodatage, ou
indique que la vidéo ne contient pas la réponse (règle combinée : plancher 0,02, seuil 0,07).

Anciennement POST /ask (schémas AskRequest/AskResponse) : renommé en POST /answer et généralisé
à tous les types de source ; la logique vidéo n'a pas changé, seule la forme de la réponse
colle maintenant au contrat {reponse, citations[], verifie} demandé pour toutes les sources.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.sources import get_owned_source, require_video_dependencies
from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.source import SourceStatus
from app.schemas.source import AnswerCitation, AnswerRequest, AnswerResponse, Passage
from app.services import papers
from app.services.video import pipeline
from app.services.video.llm import OllamaIndisponible

router = APIRouter(tags=["answer"])


def _video_to_response(source_id: str, source_title: str, r: dict) -> AnswerResponse:
    c = r.get("citation")
    citations = [AnswerCitation(chunk_id=r["passages"][c["passage"] - 1]["chunk"]["chunk_id"],
                                document_id=source_id, source=source_title, text=c["texte"],
                                timestamp=c["timestamp"])] if c else []
    rf = r.get("reformulation")
    reponse = r["reponse"]
    if rf and rf["retenue"] and not rf["identique_a_la_citation"]:
        reponse += "\n\n" + rf["texte"]
    return AnswerResponse(
        reponse=reponse,
        citations=citations,
        verifie=r["statut"] == "repondu",
        question=r["question"],
        status=r["statut"],
        passages=[Passage(chunk_id=p["chunk"]["chunk_id"], timestamp=p["chunk"]["timestamp"],
                          start=p["chunk"]["start"], end=p["chunk"]["end"], text=p["chunk"]["text"],
                          rerank=round(p["rerank"], 4))
                  for p in r["passages"]],
        timings={k: round(v, 2) for k, v in r["temps"].items()},
    )


def _paper_to_response(question: str, r: dict) -> AnswerResponse:
    return AnswerResponse(
        reponse=r["reponse"],
        citations=[AnswerCitation(**c) for c in r["citations"]],
        verifie=r["verifie"],
        question=question,
        status="repondu" if r["citations"] else "hors_sujet",
    )


@router.post("/answer", response_model=AnswerResponse)
def answer(body: AnswerRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    if papers.is_paper_id(body.source_id):
        return _paper_to_response(body.question, papers.answer(body.question, body.source_id))

    source = get_owned_source(db, body.source_id, user)
    if source.status != SourceStatus.ready:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Source is not ready (status: {source.status.value})")
    require_video_dependencies()
    try:
        return _video_to_response(source.id, source.title, pipeline.repondre(db, source, body.question))
    except OllamaIndisponible as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
