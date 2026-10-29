from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    problem: str = ""
    research_question: str = ""
    objectives: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("objectives", "hypotheses")
    @classmethod
    def clean_lines(cls, v: list[str]) -> list[str]:
        return [line.strip() for line in v if line.strip()]


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    problem: str | None = None
    research_question: str | None = None
    objectives: list[str] | None = None
    hypotheses: list[str] | None = None
    status: ProjectStatus | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class SourceCounts(BaseModel):
    pdf: int = 0
    web: int = 0
    video: int = 0
    figure: int = 0
    personal: int = 0


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: ProjectStatus
    progress: int
    sources: SourceCounts = Field(default_factory=SourceCounts)
    created_at: datetime
    updated_at: datetime


class DashboardStats(BaseModel):
    active_projects: int
    indexed_sources: int
    questions_asked: int
    pending_suggestions: int
