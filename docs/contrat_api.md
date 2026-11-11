# Contrat API — module RAG (`rag/`)

Ce document décrit les deux fonctions que les autres modules (backend, frontend) peuvent
appeler pour interroger le corpus (articles arXiv + vidéos). Elles vivent dans `rag/rag.py`.
Le module `rag/` est indépendant de `backend/` et `frontend/` (aucun de ces deux dossiers
n'est modifié par cette mission) ; une intégration devra importer `rag/rag.py` ou l'exposer
via un appel HTTP/CLI, au choix de l'équipe backend.

## `search(query: str, top_k: int = 5) -> list[dict]`

Recherche hybride (BM25 + E5 → fusion RRF → reranker MiniLM, tri stable). Renvoie les
`top_k` passages les plus pertinents, triés par score de reranking décroissant.

Chaque élément de la liste :

| champ         | type            | présent pour         | description                                              |
|---------------|-----------------|-----------------------|------------------------------------------------------------|
| `chunk_id`    | `str`           | toujours              | identifiant unique du chunk                                |
| `document_id` | `str`           | toujours              | identifiant du document (id arXiv, ou id vidéo)             |
| `source`      | `"article"\|"video"` | toujours         | type de document                                            |
| `text`        | `str`           | toujours              | texte du passage                                            |
| `score`       | `float`         | toujours              | score du reranker (probabilité, 0 à 1 ; plus haut = mieux)   |
| `timestamp`   | `str`           | si `source="video"`  | horodatage lisible `"hh:mm:ss - hh:mm:ss"`                   |

Exemple :
```python
from rag.rag import search

search("Comment TERMinator représente-t-il les acides aminés ?", top_k=3)
# [
#   {"chunk_id": "2204.13048_0007", "document_id": "2204.13048", "source": "article",
#    "text": "...", "score": 0.97},
#   ...
# ]
```

## `answer(query: str, top_k: int = 5) -> dict`

Appelle `search()`, construit un contexte avec les passages trouvés, puis demande à
**qwen2.5:3b** (seul LLM autorisé, via Ollama local `http://localhost:11434`) de répondre
en français en citant les extraits utilisés (`[1]`, `[2]`, ...).

```python
{
    "reponse": str,        # texte généré par le LLM (ou message de rejet si rien de pertinent)
    "citations": [          # extraits que le LLM dit avoir utilisés (ou le meilleur si aucune
                             # citation explicite n'a été détectée dans le texte)
        {"chunk_id": str, "document_id": str, "source": "article" | "video"},
        ...
    ],
    "verifie": bool,        # True seulement si : au moins un passage dépasse le plancher de
                             # confiance du reranker (0.02) ET le LLM a cité au moins un extrait
}
```

### Règle de `verifie`

- Si le meilleur score de reranking est sous le plancher (0.02) → pas de recherche de
  réponse, `verifie=False`, `citations=[]`, message standard de rejet.
- Sinon, le LLM génère une réponse. Chaque extrait fourni est noté par recouvrement
  lexical avec la réponse (fonction `couverture`, reprise de
  `backend/app/services/video/text.py`, lecture seule) ; un extrait est retenu comme
  citation si son score dépasse `SEUIL_COUVERTURE` (0.10). `verifie=True` seulement s'il
  y a au moins une citation retenue.
  - Première version : citation détectée en cherchant littéralement `[1]`, `[2]`, ... dans
    le texte généré. Abandonnée : qwen2.5:3b ne reprend presque jamais ce format, donc
    `verifie` restait `False` même pour des réponses correctes (voir le rapport de fin de
    mission).
  - Le seuil 0.10 est volontairement bas : le corpus d'articles est en anglais et les
    réponses sont en français, donc le recouvrement lexical vient surtout des termes
    techniques et noms propres partagés, jamais d'une traduction mot à mot. **`verifie=True`
    signifie que la réponse est ancrée dans un passage retrouvé, pas que ce passage est le
    bon** : sur l'échantillon de test, 2/5 réponses sont « vérifiées » alors que le passage
    pertinent attendu n'était même pas dans le top 10 de la recherche.

**Limites connues** (voir le rapport de fin de mission pour le détail) : un seul appel LLM
génère la réponse (pas de second appel de vérification séparé, pas de réécriture de
requête, pas de mode extractif, contrairement au prototype vidéo complet
`D:\Transcription\rag.py`). Le seuil 0.10 n'a été calibré que sur 5 questions, toutes dans
le sujet du corpus ; son comportement sur des questions hors sujet n'a pas été testé.

## Données attendues

`search()`/`answer()` chargent `rag/data/chunks.jsonl` (un objet JSON par ligne, voir
`rag/chunking.py` pour le schéma commun article/vidéo). Le premier appel construit l'index
(BM25 + embeddings E5 de tous les chunks) : **~13 minutes sur CPU pour les 3867 chunks des
139 articles** sur cette machine — l'index n'est pas mis en cache sur disque pour l'instant
(voir le rapport de fin de mission).
