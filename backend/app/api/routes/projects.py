from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import DashboardStats, ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _split(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _join(lines: list[str]) -> str:
    return "\n".join(lines)


def to_read(p: Project) -> ProjectRead:
    return ProjectRead(
        id=p.id,
        title=p.title,
        problem=p.problem,
        research_question=p.research_question,
        objectives=_split(p.objectives),
        hypotheses=_split(p.hypotheses),
        status=p.status,
        progress=p.progress,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _get_owned(db: Session, project_id: str, user: CurrentUser) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    if project is None:
        # 404 (not 403) so a user cannot probe for other users' project ids.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    rows = db.scalars(
        select(Project).where(Project.user_id == user.id).order_by(Project.updated_at.desc())
    ).all()
    return [to_read(p) for p in rows]


@router.get("/stats", response_model=DashboardStats)
def project_stats(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    count = db.scalar(select(func.count()).select_from(Project).where(Project.user_id == user.id)) or 0
    # Sources, questions and suggestions arrive with their own modules.
    return DashboardStats(active_projects=count, indexed_sources=0, questions_asked=0, pending_suggestions=0)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    project = Project(
        user_id=user.id,
        title=body.title,
        problem=body.problem.strip(),
        research_question=body.research_question.strip(),
        objectives=_join(body.objectives),
        hypotheses=_join(body.hypotheses),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return to_read(project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return to_read(_get_owned(db, project_id, user))


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = _get_owned(db, project_id, user)
    data = body.model_dump(exclude_unset=True)
    for key in ("objectives", "hypotheses"):
        if data.get(key) is not None:
            data[key] = _join([line.strip() for line in data[key] if line.strip()])
    if data.get("title") is not None:
        data["title"] = data["title"].strip()
    for key, value in data.items():
        if value is not None:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return to_read(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    project = _get_owned(db, project_id, user)
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
