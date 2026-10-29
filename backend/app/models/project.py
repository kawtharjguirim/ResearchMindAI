import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectStatus(str, enum.Enum):
    in_progress = "in_progress"
    literature_review = "literature_review"
    writing = "writing"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Supabase user id (the `sub` claim). Every query filters on it: data isolation.
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    problem: Mapped[str] = mapped_column(Text, default="", nullable=False)
    research_question: Mapped[str] = mapped_column(Text, default="", nullable=False)
    objectives: Mapped[str] = mapped_column(Text, default="", nullable=False)  # one per line
    hypotheses: Mapped[str] = mapped_column(Text, default="", nullable=False)  # one per line

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=32),
        default=ProjectStatus.in_progress,
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
