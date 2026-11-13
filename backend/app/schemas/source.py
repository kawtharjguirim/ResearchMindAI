from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.source import SourceStatus

# Types affichables par le frontend (components/ui.tsx: SOURCE_TYPES). "video" est le seul type
# réellement traité aujourd'hui ; les autres ne viennent que des sources papier simulées
# (app.services.papers) en attendant le contrat du corpus arXiv.
AnySourceType = Literal["pdf", "web", "figure", "video", "personal"]


class SourceRead(BaseModel):
    id: str
    project_id: str | None
    source_type: AnySourceType
    title: str
    url: str
    language: str | None
    duration: float | None
    status: SourceStatus
    error: str
    chunk_count: int
    excerpt: str | None = None   # résumé court (sources papier uniquement)
    created_at: datetime
    updated_at: datetime


class AnswerRequest(BaseModel):
    source_id: str
    question: str = Field(min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        return v


class Passage(BaseModel):
    chunk_id: str
    timestamp: str
    start: float
    end: float
    text: str
    rerank: float


class AnswerCitation(BaseModel):
    """Une citation de la réponse : passage vidéo (timestamp) ou passage papier (url)."""
    chunk_id: str
    document_id: str
    source: str                   # titre de la source citée
    text: str                     # phrase exacte citée
    timestamp: str | None = None  # horodatage vidéo "hh:mm:ss" (absent pour une source papier)
    url: str | None = None        # lien de la source papier (absent pour une vidéo)


class PaperPassage(BaseModel):
    chunk_id: str
    section: str
    text: str


class PaperSummary(BaseModel):
    """Article arXiv du corpus, tel qu'affiché dans la bibliothèque."""
    doc_id: str
    title: str
    domain: str
    categories: str
    authors: str
    update_date: str
    license: str
    arxiv_url: str
    abstract: str
    has_pdf: bool


class PaperRead(PaperSummary):
    """Article arXiv du corpus, avec le passage cité si un chunk_id est demandé."""
    passage: PaperPassage | None = None


class AnswerResponse(BaseModel):
    """Contrat générique {reponse, citations, verifie}, quel que soit le type de source."""
    reponse: str
    citations: list[AnswerCitation]
    verifie: bool
    # Champs additionnels utiles à l'UI (passages lus, temps par étape) : vides pour une
    # source papier simulée tant que son contrat réel n'est pas branché.
    question: str
    status: Literal["repondu", "confiance_faible", "hors_sujet"] = "repondu"
    passages: list[Passage] = []
    timings: dict[str, float] = {}


class PlayLink(BaseModel):
    url: str
    expires_at: datetime


class TranscriptChunk(BaseModel):
    chunk_id: str
    start: float
    end: float
    timestamp: str
    text: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    source_id: str | None = None   # limite la recherche à cette source ; sinon toutes les sources prêtes
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    source: str
    text: str
    score: float
    timestamp: str | None = None
