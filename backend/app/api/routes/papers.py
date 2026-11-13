"""
Articles arXiv du corpus (voir app.services.arxiv_docs) :

    GET /papers                            ->  bibliothèque : tous les articles du corpus
    GET /papers/{doc_id}?chunk=<chunk_id>  ->  métadonnées + passage cité (optionnel)
    GET /papers/{doc_id}/pdf               ->  le PDF compilé

Le PDF passe par une requête authentifiée (le frontend le charge en blob), pas par un lien signé.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.auth import CurrentUser, get_current_user
from app.schemas.source import PaperPassage, PaperRead, PaperSummary
from app.services import arxiv_docs

router = APIRouter(prefix="/papers", tags=["papers"])


def _resume(d: dict) -> dict:
    return {
        "doc_id": d["doc_id"], "title": d.get("title", ""), "domain": d.get("domain", ""),
        "categories": d.get("categories", ""), "authors": d.get("authors", ""),
        "update_date": d.get("update_date", ""), "license": d.get("license", ""),
        "arxiv_url": d.get("arxiv_url", ""), "abstract": d.get("abstract", ""),
        "has_pdf": arxiv_docs.pdf_path(d["doc_id"]) is not None,
    }


def _document_ou_404(doc_id: str) -> dict:
    d = arxiv_docs.document(doc_id)
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return d


@router.get("", response_model=list[PaperSummary])
def list_papers(_: CurrentUser = Depends(get_current_user)):
    return sorted((_resume(d) for d in arxiv_docs.documents()), key=lambda p: p["title"].lower())


@router.get("/{doc_id}", response_model=PaperRead)
def get_paper(doc_id: str, chunk: str | None = None, _: CurrentUser = Depends(get_current_user)):
    d = _document_ou_404(doc_id)
    p = arxiv_docs.passage(doc_id, chunk) if chunk else None
    return PaperRead(**_resume(d), passage=PaperPassage(**p) if p else None)


@router.get("/{doc_id}/pdf")
def get_paper_pdf(doc_id: str, _: CurrentUser = Depends(get_current_user)):
    _document_ou_404(doc_id)
    chemin = arxiv_docs.pdf_path(doc_id)
    if chemin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No PDF for this paper")
    return FileResponse(chemin, media_type="application/pdf")
