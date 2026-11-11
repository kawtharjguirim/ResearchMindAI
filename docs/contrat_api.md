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
- Sinon, le LLM génère une réponse ; `verifie=True` seulement s'il a cité au moins un des
  extraits fournis (détection de `[1]`, `[2]`, ... dans le texte généré).

**Limite connue** (voir le rapport de fin de mission pour le détail) : cette règle est une
version simplifiée de celle du prototype vidéo (`D:\Transcription\rag.py`), qui utilise un
second appel LLM dédié à la vérification. Ici, un seul appel génère la réponse ; il n'y a
pas de réécriture de requête ni de mode extractif. À valider/durcir avant mise en
production si la fiabilité de `verifie` doit être plus stricte.

## Données attendues

`search()`/`answer()` chargent `rag/data/chunks.jsonl` (un objet JSON par ligne, voir
`rag/chunking.py` pour le schéma commun article/vidéo). Le premier appel construit l'index
(BM25 + embeddings E5 de tous les chunks) : **~13 minutes sur CPU pour les 3867 chunks des
139 articles** sur cette machine — l'index n'est pas mis en cache sur disque pour l'instant
(voir le rapport de fin de mission).
