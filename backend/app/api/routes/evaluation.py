"""
Relecture humaine du jeu de test du corpus (rag/eval/jeu_corpus.json, voir rag/eval/assembler_jeu.py) :

    GET   /evaluation/questions        ->  questions + passage vise
    PATCH /evaluation/questions/{id}   ->  statut, correction, commentaire (ecrit dans le fichier)

Outil de recherche partage : tout utilisateur connecte peut relire. Le fichier est la source de verite
(versionne avec le depot), reecrit de facon atomique.
"""
import json
import os
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.schemas.evaluation import EvalQuestion, EvalQuestionUpdate

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

EVAL_DIR = Path(__file__).resolve().parents[4] / "rag" / "eval"
_verrou = threading.Lock()


def _lire_jeu() -> dict:
    chemin = EVAL_DIR / "jeu_corpus.json"
    if not chemin.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No evaluation set: run rag/eval/assembler_jeu.py first.")
    return json.loads(chemin.read_text(encoding="utf-8"))


def _ecrire_jeu(jeu: dict) -> None:
    chemin = EVAL_DIR / "jeu_corpus.json"
    tmp = chemin.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(jeu, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, chemin)


def _passages() -> dict[str, dict]:
    chemin = EVAL_DIR / "passages_echantillon.json"
    return {p["chunk_id"]: p for p in json.loads(chemin.read_text(encoding="utf-8"))}


def _avec_passage(q: dict, passages: dict[str, dict]) -> EvalQuestion:
    p = passages.get(q["chunk_id"], {})
    return EvalQuestion(**q, titre=p.get("titre", ""), section=p.get("section", ""), passage=p.get("texte", ""))


@router.get("/questions", response_model=list[EvalQuestion])
def list_questions(_: CurrentUser = Depends(get_current_user)):
    passages = _passages()
    return [_avec_passage(q, passages) for q in _lire_jeu()["questions"]]


@router.patch("/questions/{question_id}", response_model=EvalQuestion)
def update_question(question_id: str, body: EvalQuestionUpdate, _: CurrentUser = Depends(get_current_user)):
    with _verrou:
        jeu = _lire_jeu()
        q = next((x for x in jeu["questions"] if x["id"] == question_id), None)
        if q is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        for champ, valeur in body.model_dump(exclude_none=True).items():
            q[champ] = valeur.strip() if isinstance(valeur, str) and champ != "statut" else valeur
        _ecrire_jeu(jeu)
    return _avec_passage(q, _passages())
