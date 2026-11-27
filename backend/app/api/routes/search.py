"""
Recherche seule (sans génération) sur les sources de l'utilisateur : vidéos réelles
(app.services.video.search, recherche hybride BM25+E5+reranker) et sources papier
(app.services.papers : corpus arXiv réel si rag/ est disponible, sinon résultats simulés).

    POST /search  {"query": "...", "source_id": "..." (optionnel), "top_k": 5}
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.source import Chunk, Source, SourceStatus
from app.schemas.source import SearchRequest, SearchResult
from app.services import papers
from app.services.rag_corpus import RagIndisponible
from app.services.video import pipeline

router = APIRouter(tags=["search"])


def _search_video(db: Session, source: Source, query: str, top_k: int) -> list[SearchResult]:
    chunks = db.scalars(select(Chunk).where(Chunk.source_id == source.id).order_by(Chunk.position)).all()
    if not chunks:
        return []
    index = pipeline.index_pour(source, list(chunks))
    resultats = index.rechercher(query)[:top_k]
    return [SearchResult(chunk_id=r["chunk"]["chunk_id"], document_id=source.id, source=source.title,
                         text=r["chunk"]["text"], score=round(r["rerank"], 4),
                         timestamp=r["chunk"]["timestamp"])
            for r in resultats]


@router.post("/search", response_model=list[SearchResult])
def search(body: SearchRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    try:
        if body.source_id:
            if papers.is_paper_id(body.source_id):
                return [SearchResult(**r) for r in papers.search(body.query, body.source_id, body.top_k)]
            source = db.scalar(select(Source).where(Source.id == body.source_id, Source.user_id == user.id,
                                                     Source.status == SourceStatus.ready))
            return _search_video(db, source, body.query, body.top_k) if source else []

        # Pas de source précisée : toutes les vidéos prêtes de l'utilisateur, plus les sources papier.
        resultats: list[SearchResult] = []
        sources = db.scalars(select(Source).where(Source.user_id == user.id, Source.status == SourceStatus.ready)).all()
        for source in sources:
            resultats += _search_video(db, source, body.query, body.top_k)
        resultats += [SearchResult(**r) for r in papers.search(body.query, None, body.top_k)]
        resultats.sort(key=lambda r: r.score, reverse=True)
        return resultats[:body.top_k]
    except RagIndisponible as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
