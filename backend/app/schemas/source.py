from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.source import SourceStatus, SourceType


class SourceRead(BaseModel):
    id: str
    project_id: str | None
    source_type: SourceType
    title: str
    url: str
    language: str | None
    duration: float | None
    status: SourceStatus
    error: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class AskRequest(BaseModel):
    source_id: str
    question: str = Field(min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        return v


class Citation(BaseModel):
    text: str                 # phrase exacte de la transcription
    timestamp: str            # "hh:mm:ss" du début de la citation
    passage: int              # numéro du passage (1..TOP_K) qui la contient


class Passage(BaseModel):
    chunk_id: str
    timestamp: str
    start: float
    end: float
    text: str
    rerank: float


class AskResponse(BaseModel):
    question: str
    # repondu : citation trouvée ; confiance_faible : à vérifier ; hors_sujet : la vidéo ne répond pas
    status: Literal["repondu", "confiance_faible", "hors_sujet"]
    answer: str
    citation: Citation | None
    rephrasing: str | None    # reformulation du LLM, seulement si elle a passé les contrôles
    passages: list[Passage]   # passages lus (TOP_K), du plus pertinent au moins pertinent
    timings: dict[str, float]
