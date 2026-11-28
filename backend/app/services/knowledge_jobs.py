"""
Tâches d'extraction en arrière-plan : un document importé, ou des articles du corpus.

Chaque tâche a une ligne KnowledgeJob (progression visible par GET /knowledge/jobs/{id}).
Les fonctions de ce module s'exécutent dans une session à part : elles ne dépendent pas de la requête HTTP.
"""
import logging
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.knowledge import KnowledgeJob
from app.models.source import Chunk, Source
from app.services import extraction
from app.services.documents import decouper_pages, lire_pages
from app.services.video import llm

logger = logging.getLogger(__name__)

# backend/app/services/knowledge_jobs.py -> racine du projet -> data_latex/data/pdf
PDF_CORPUS = Path(__file__).resolve().parents[3] / "data_latex" / "data" / "pdf"


def ids_corpus(limite: int) -> list[str]:
    """Identifiants des articles du corpus disponibles en PDF, dans l'ordre alphabétique."""
    return sorted({p.stem for p in PDF_CORPUS.glob("*/*.pdf")})[:limite]


def passages_corpus(identifiant: str) -> list[dict]:
    """Passages (page par page) d'un article du corpus. Liste vide si son PDF est introuvable."""
    chemins = list(PDF_CORPUS.glob(f"*/{identifiant}.pdf"))
    if not chemins:
        return []
    return [{"text": c["text"], "location": c["timestamp"]} for c in decouper_pages(lire_pages(chemins[0]))]


def passages_source(db, source: Source) -> list[dict]:
    """Passages déjà découpés d'une source importée, avec leur page ou leur horodatage."""
    chunks = db.scalars(select(Chunk).where(Chunk.source_id == source.id).order_by(Chunk.position)).all()
    return [{"text": c.text, "location": c.timestamp} for c in chunks]


def _mettre_a_jour(db, job: KnowledgeJob, **champs) -> None:
    for cle, valeur in champs.items():
        setattr(job, cle, valeur)
    db.commit()


def executer_source(job_id: str, user_id: str, source_id: str) -> None:
    """Extrait les propositions d'un document importé. Ne lève jamais : l'erreur va dans le job."""
    with SessionLocal() as db:
        job = db.get(KnowledgeJob, job_id)
        source = db.scalar(select(Source).where(Source.id == source_id, Source.user_id == user_id))
        if job is None:
            return
        if source is None:
            _mettre_a_jour(db, job, status="failed", message="Document introuvable.")
            return
        try:
            passages = passages_source(db, source)
            selection = extraction.selectionner(passages)
            _mettre_a_jour(db, job, status="running", total=len(selection), message="Extraction en cours.")

            def progres(fait: int, total: int) -> None:
                _mettre_a_jour(db, job, progress=fait, total=total)

            bilan = extraction.extraire_document(db, user_id, f"source:{source.id}", source.title, passages,
                                                 progres=progres)
            _mettre_a_jour(db, job, status="done", progress=bilan["passages_lus"], message=_resume(bilan))
        except llm.OllamaIndisponible as e:
            db.rollback()
            _mettre_a_jour(db, job, status="failed", message=str(e))
        except Exception as e:  # noqa: BLE001 : l'erreur est affichée dans la tâche
            logger.exception("Extraction du document %s en échec", source_id)
            db.rollback()
            _mettre_a_jour(db, job, status="failed", message=f"{type(e).__name__}: {e}"[:2000])


def executer_corpus(job_id: str, user_id: str, identifiants: list[str]) -> None:
    """Extrait les propositions de plusieurs articles du corpus, un par un."""
    with SessionLocal() as db:
        job = db.get(KnowledgeJob, job_id)
        if job is None:
            return
        _mettre_a_jour(db, job, status="running", total=len(identifiants), message="Extraction en cours.")
        bilan_total = {"passages_lus": 0, "proposees": 0, "a_relire": 0, "rejetees": 0, "doublons": 0}
        try:
            for i, identifiant in enumerate(identifiants):
                passages = passages_corpus(identifiant)
                if passages:
                    bilan = extraction.extraire_document(db, user_id, f"corpus:{identifiant}",
                                                         f"arXiv:{identifiant}", passages)
                    for cle in bilan_total:
                        bilan_total[cle] += bilan[cle]
                _mettre_a_jour(db, job, progress=i + 1, message=f"{identifiant} traité.")
            _mettre_a_jour(db, job, status="done", message=_resume(bilan_total))
        except llm.OllamaIndisponible as e:
            db.rollback()
            _mettre_a_jour(db, job, status="failed", message=str(e))
        except Exception as e:  # noqa: BLE001
            logger.exception("Extraction du corpus en échec")
            db.rollback()
            _mettre_a_jour(db, job, status="failed", message=f"{type(e).__name__}: {e}"[:2000])


def _resume(bilan: dict) -> str:
    return (f"{bilan['proposees']} propositions ({bilan['a_relire']} à relire), "
            f"{bilan['rejetees']} rejetées, {bilan['doublons']} déjà connues, "
            f"{bilan['passages_lus']} passages lus.")
