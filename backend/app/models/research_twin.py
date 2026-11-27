import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchTwin(Base):
    __tablename__ = "research_twins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    problem: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    research_question: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    objectives: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    hypotheses: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    methods: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    limitations: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    research_gaps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
