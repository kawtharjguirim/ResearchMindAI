"""
Sources de connaissances et leurs chunks. Pour l'instant : vidéos (module « capsule vidéo »).

Source : une vidéo importée par un utilisateur, avec l'état de son traitement et ses segments
         de transcription (gardés pour horodater précisément les citations).
Chunk  : un passage de la transcription, avec sa provenance (début/fin) et son vecteur E5,
         pour reconstruire l'index de recherche sans recalculer les embeddings.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class SourceType(str, enum.Enum):
    video = "video"
    web = "web"
    pdf = "pdf"
    personal = "personal"   # document personnel : Word, Markdown ou texte
    figure = "figure"   # image importée (texte reconnu par OCR)


class SourceStatus(str, enum.Enum):
    pending = "pending"            # importée, en attente de traitement
    transcribing = "transcribing"
    indexing = "indexing"          # découpage + embeddings
    ready = "ready"
    error = "error"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Supabase user id (the `sub` claim). Every query filters on it: data isolation.
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )

    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False, length=16), default=SourceType.video, nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), default="", nullable=False)  # dans backend/storage
    url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)  # secondes

    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, native_enum=False, length=16), default=SourceStatus.pending, nullable=False
    )
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Segments Whisper [{start, end, text}] : horodatage précis des citations
    segments: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="source", cascade="all, delete-orphan", order_by="Chunk.position"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # ordre dans la vidéo

    start: Mapped[float] = mapped_column(Float, nullable=False)  # secondes
    end: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(32), nullable=False)  # "hh:mm:ss - hh:mm:ss"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Vecteur E5 normalisé (384 floats), facultatif
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    source: Mapped[Source] = relationship(back_populates="chunks")

    def as_search_chunk(self) -> dict:
        """Format attendu par app.services.video.search.Index et qa.VideoQA."""
        s = self.source
        return {"chunk_id": self.id, "document_id": s.id, "source_type": s.source_type.value,
                "source": s.url or s.filename, "title": s.title, "language": s.language,
                "start": self.start, "end": self.end, "timestamp": self.timestamp, "text": self.text}
