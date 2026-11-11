# rag/ — chunking, recherche hybride et generation (articles + videos)

Module independant de `backend/` et `frontend/` (aucun des deux n'est modifie par cette
mission). Contrat API pour l'integration : [`docs/contrat_api.md`](../docs/contrat_api.md).

| fichier            | role                                                                          |
|--------------------|--------------------------------------------------------------------------------|
| `chunking.py`      | chunking unifie articles (.tex, via `data_latex/scripts/chunk_embed.py`) + videos |
| `recherche.py`     | classe `Index` : BM25 + E5 -> fusion RRF -> reranker MiniLM (tri stable)        |
| `rag.py`           | `search(query, top_k)` et `answer(query)` -- LLM qwen2.5:3b (Ollama local)      |
| `rouge.py`         | ROUGE-1/2/L (sans dependance externe)                                          |
| `evaluation.py`    | Recall@1/@3, MRR@10 et ROUGE sur `eval/eval_questions.json`                     |
| `eval/`            | jeu de questions d'evaluation (ecrit a la main, voir plus bas)                  |
| `results/`         | sorties de `evaluation.py` (CSV)                                               |
| `data/`            | `chunks.jsonl` genere (non versionne, voir `.gitignore`)                        |

## Utilisation

```bash
# 1. Construire les chunks (articles data_latex + videos deja decoupees, en option)
python -I chunking.py --out data/chunks.jsonl

# 2. Interroger (premier appel : construit l'index, ~13 min sur CPU pour 3867 chunks)
python -I rag.py "Comment TERMinator represente-t-il les acides amines ?"

# 3. Evaluer (retrieval + ROUGE)
python -I evaluation.py --chunks data/chunks.jsonl --questions eval/eval_questions.json
```

Necessite `sentence-transformers`, `rank-bm25` et `numpy` (deja installes dans
`backend/.venv` pour le module video ; sinon `pip install sentence-transformers rank-bm25
numpy`), et un serveur Ollama local avec `qwen2.5:3b` (`ollama pull qwen2.5:3b`).

## Jeu d'evaluation

`eval/eval_questions.json` contient 5 questions (une par domaine du corpus) ecrites a la
main pour cette mission, faute de jeu de questions-reponses existant pour les articles
(celui de `D:\Transcription\eval_questions_dur.json` ne couvre qu'une seule video). Chaque
question donne : le(s) `chunk_id` pertinent(s), et une reponse de reference en francais
fidele au contenu de ce chunk, utilisee pour calculer ROUGE. C'est un echantillon
illustratif, pas un jeu de validation exhaustif -- voir le rapport de fin de mission.
