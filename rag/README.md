# rag/ — chunking, recherche hybride et generation (articles + videos)

Module independant de `backend/` et `frontend/` (aucun des deux n'est modifie par cette
mission). Contrat API pour l'integration : [`docs/contrat_api.md`](../docs/contrat_api.md).

| fichier            | role                                                                          |
|--------------------|--------------------------------------------------------------------------------|
| `chunking.py`      | chunking unifie articles (.tex, via `data_latex/scripts/chunk_embed.py`) + videos |
| `recherche.py`     | classe `Index` : BM25 + E5 -> fusion RRF -> reranker, configure par `config_recherche.json` |
| `config_recherche.json` | parametres du systeme retenu au notebook 10 (modele, BM25, fusion, reranker) |
| `parite.py`        | test de parite : `recherche.py` reproduit-il le notebook 10 sur SciFact ?        |
| `rag.py`           | `search(query, top_k)` et `answer(query)` -- LLM qwen2.5:3b (Ollama local)      |
| `rouge.py`         | ROUGE-1/2/L (sans dependance externe)                                          |
| `evaluation.py`    | Recall@1/@3, MRR@10 et ROUGE sur `eval/eval_questions.json`                     |
| `eval/`            | jeu de questions d'evaluation (ecrit a la main, voir plus bas)                  |
| `results/`         | sorties de `evaluation.py` et `parite.py` (CSV)                                 |
| `data/`            | `chunks.jsonl` et `cache/` des embeddings (non versionnes, voir `.gitignore`)   |

## Utilisation

```bash
# 1. Construire les chunks (articles data_latex + videos deja decoupees, en option)
python -I chunking.py --out data/chunks.jsonl

# 2. Interroger (premier appel : encode les passages une seule fois, puis cache disque)
python -I rag.py "Comment TERMinator represente-t-il les acides amines ?"

# 3. Evaluer (retrieval + ROUGE)
python -I evaluation.py --chunks data/chunks.jsonl --questions eval/eval_questions.json

# 4. Verifier la parite avec le notebook 10 (a relancer apres tout changement de config_recherche.json)
python -I parite.py --experiences ../../ResearchMind1/ResearchMind-AI
```

## Integrite du pipeline

`recherche.py` ne choisit aucun parametre : il lit `config_recherche.json`, qui decrit le
systeme retenu au notebook 10 du depot d'experimentation. `parite.py` rejoue SciFact (test)
avec ce module et le compare aux sorties du notebook (embeddings, run BM25, nDCG@10 de
`results/metrics.csv`) ; le reranker n'est pas encore couvert, faute de resultats du
notebook 11.

Necessite `sentence-transformers`, `nltk`, `scikit-learn`, `scipy` et `numpy` (groupe
`video` de `backend/pyproject.toml`), et un serveur Ollama local avec `qwen2.5:3b`
(`ollama pull qwen2.5:3b`).

## Jeu d'evaluation

`eval/eval_questions.json` contient 5 questions (une par domaine du corpus) ecrites a la
main pour cette mission, faute de jeu de questions-reponses existant pour les articles
(celui de `D:\Transcription\eval_questions_dur.json` ne couvre qu'une seule video). Chaque
question donne : le(s) `chunk_id` pertinent(s), et une reponse de reference en francais
fidele au contenu de ce chunk, utilisee pour calculer ROUGE. C'est un echantillon
illustratif, pas un jeu de validation exhaustif -- voir le rapport de fin de mission.
