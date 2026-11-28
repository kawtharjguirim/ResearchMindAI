"""
Propositions du graphe de connaissances : extraction, suivi, validation et historique.

    POST /knowledge/extract/source/{source_id}   lance l'extraction d'un document importé (tâche)
    POST /knowledge/extract/corpus?limit=N       lance l'extraction de N articles du corpus (tâche)
    GET  /knowledge/jobs/{job_id}                état et progression d'une tâche
    GET  /knowledge/proposals?status=pending     propositions en attente (ou approved, rejected)
    POST /knowledge/proposals/{id}/approve       approuve et écrit dans Neo4j
    POST /knowledge/proposals/{id}/reject        rejette, sans rien écrire
    GET  /knowledge/history                      propositions déjà décidées
"""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.knowledge import KnowledgeJob, KnowledgeProposal
from app.models.source import Source
from app.services import knowledge_graph as kg
from app.services import knowledge_jobs

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _lire_proposition(p: KnowledgeProposal) -> dict:
    return {
        "id": p.id, "document_key": p.document_key, "document_title": p.document_title,
        "entity_type": p.entity_type, "name": p.name, "excerpt": p.excerpt, "location": p.location,
        "verification_status": p.verification_status, "status": p.status,
        "extraction_date": p.extraction_date, "decided_at": p.decided_at,
    }


def _lire_job(j: KnowledgeJob) -> dict:
    return {"id": j.id, "kind": j.kind, "target": j.target, "status": j.status, "progress": j.progress,
            "total": j.total, "message": j.message, "created_at": j.created_at, "updated_at": j.updated_at}


def _nouvelle_tache(db: Session, user: CurrentUser, kind: str, target: str) -> KnowledgeJob:
    job = KnowledgeJob(user_id=user.id, kind=kind, target=target)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _proposition_de_l_utilisateur(db: Session, proposition_id: str, user: CurrentUser) -> KnowledgeProposal:
    p = db.scalar(select(KnowledgeProposal).where(KnowledgeProposal.id == proposition_id,
                                                   KnowledgeProposal.user_id == user.id))
    if p is None:
        # 404 et non 403 : on ne révèle pas l'existence des propositions d'un autre utilisateur.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return p


@router.post("/extract/source/{source_id}", status_code=status.HTTP_202_ACCEPTED)
def extract_source(source_id: str, background: BackgroundTasks, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(get_current_user)):
    source = db.scalar(select(Source).where(Source.id == source_id, Source.user_id == user.id))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    if source.status.value != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Source is not ready")
    job = _nouvelle_tache(db, user, "source", source_id)
    background.add_task(knowledge_jobs.executer_source, job.id, user.id, source_id)
    return _lire_job(job)


@router.post("/extract/corpus", status_code=status.HTTP_202_ACCEPTED)
def extract_corpus(background: BackgroundTasks, limit: int = Query(default=3, ge=1, le=80),
                   db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    """Articles du corpus, un par un. Chaque article prend plusieurs minutes sur CPU : limite faible par défaut."""
    identifiants = knowledge_jobs.ids_corpus(limit)
    if not identifiants:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No corpus PDF found")
    job = _nouvelle_tache(db, user, "corpus", f"{len(identifiants)} articles")
    background.add_task(knowledge_jobs.executer_corpus, job.id, user.id, identifiants)
    return _lire_job(job)


@router.get("/jobs/{job_id}")
def job(job_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    j = db.scalar(select(KnowledgeJob).where(KnowledgeJob.id == job_id, KnowledgeJob.user_id == user.id))
    if j is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _lire_job(j)


@router.get("/proposals")
def proposals(status_filtre: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected)$"),
              document_key: str | None = None, db: Session = Depends(get_db),
              user: CurrentUser = Depends(get_current_user)):
    requete = select(KnowledgeProposal).where(KnowledgeProposal.user_id == user.id,
                                              KnowledgeProposal.status == status_filtre)
    if document_key:
        requete = requete.where(KnowledgeProposal.document_key == document_key)
    lignes = db.scalars(requete.order_by(KnowledgeProposal.extraction_date.desc())).all()
    return [_lire_proposition(p) for p in lignes]


@router.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    p = _proposition_de_l_utilisateur(db, proposal_id, user)
    if p.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Proposal already {p.status}")
    try:
        driver = kg.pilote()
        try:
            kg.ajouter_proposition(driver, _lire_proposition(p) | {"normalized_name": p.normalized_name}, user.id)
        finally:
            driver.close()
    except Exception as e:  # noqa: BLE001 : Neo4j absent : la proposition reste en attente
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Neo4j unavailable ({type(e).__name__}). The proposal stays pending.") from e
    p.status = "approved"
    p.decided_at = datetime.now(timezone.utc)
    db.commit()
    return _lire_proposition(p)


@router.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    p = _proposition_de_l_utilisateur(db, proposal_id, user)
    if p.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Proposal already {p.status}")
    p.status = "rejected"
    p.decided_at = datetime.now(timezone.utc)
    db.commit()
    return _lire_proposition(p)


@router.get("/history")
def history(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    lignes = db.scalars(select(KnowledgeProposal).where(
        KnowledgeProposal.user_id == user.id, KnowledgeProposal.status != "pending"
    ).order_by(KnowledgeProposal.decided_at.desc())).all()
    return [_lire_proposition(p) for p in lignes]
