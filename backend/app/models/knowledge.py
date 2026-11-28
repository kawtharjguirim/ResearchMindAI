"""
Propositions d'entités scientifiques extraites des documents, et suivi des tâches d'extraction.

KnowledgeProposal : une méthode, un jeu de données, un résultat ou un concept proposé à partir d'un
passage. Rien n'est écrit dans Neo4j tant que l'utilisateur ne l'a pas approuvé.
KnowledgeJob     : une extraction en cours ou terminée (progression visible par l'interface).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# Valeurs possibles (chaînes, pour rester lisibles en base) :
#   entity_type         : Method, Dataset, Result, Concept
#   verification_status : VERIFIED, NEEDS_REVIEW, REJECTED
#   status              : pending, approved, rejected
class KnowledgeProposal(Base):
    __tablename__ = "knowledge_proposals"
    __table_args__ = (
        # Une même entité, dans le même passage, n'est proposée qu'une fois (relance idempotente).
        UniqueConstraint("user_id", "document_key", "entity_type", "normalized_name", "location",
                         name="uq_proposition_passage"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    document_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)  # corpus:<id> ou source:<uuid>
    document_title: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)   # phrase exacte du passage
    location: Mapped[str] = mapped_column(String(40), default="", nullable=False)  # « p. 3 », « § 2 »…
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    extraction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeJob(Base):
    __tablename__ = "knowledge_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)          # source, corpus
    target: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)  # queued, running, done, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
