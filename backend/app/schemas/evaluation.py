from typing import Literal

from pydantic import BaseModel, Field

Statut = Literal["a_valider", "valide", "corrige", "rejete"]


class EvalQuestion(BaseModel):
    id: str
    domaine: str
    split: Literal["validation", "test"]
    document_id: str
    chunk_id: str
    titre: str
    section: str
    passage: str
    question: str
    reference: str
    question_initiale: str
    reference_initiale: str
    auteur: str
    statut: Statut
    commentaire: str


class EvalQuestionUpdate(BaseModel):
    statut: Statut | None = None
    question: str | None = Field(default=None, min_length=5, max_length=1000)
    reference: str | None = Field(default=None, min_length=1, max_length=3000)
    commentaire: str | None = Field(default=None, max_length=1000)
