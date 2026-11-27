# Plan de correction — intégration du pipeline complet

> Référence : *ResearchMind AI — Cahier des Charges* (`Cahier-de-charge_ReserachMind-AI.pdf`), sections 8, 11 à 43.
> État constaté le 2026-11-12 sur la branche `Mohamed` et dans le dépôt d'expérimentation
> `D:\ResearchMind\ResearchMind1\ResearchMind-AI` (notebooks 01 à 11, dossier `results/`).
>
> **Règle** : aucune valeur de ce document n'est estimée. Les chiffres cités viennent des fichiers
> de résultats existants. Le tableau de la section 21 du cahier ne sera rempli qu'avec des
> mesures réelles.

---

## 0. Pipeline cible (cahier, section 43)

```
PDF / WEB / IMAGES / VIDÉOS / DOCUMENTS PERSONNELS
  → Ingestion → Prétraitement → Dataset → Baseline → ML → DL → Transfer Learning
  → Fine-Tuning → Évaluation → Comparaison → Sélection → Intégration
  → RAG → Knowledge Graph → Research Twin → Agents → SaaS
```

## 1. État de départ

| Étape | État | Constat |
|---|---|---|
| Ingestion | ⚠️ 2/5 | Articles arXiv (139, extraits du `.tex`, préparés hors application) et vidéos (fichier importé, transcrit). Absents : YouTube par URL, Web, images/OCR, documents personnels, import de PDF dans l'app. |
| Prétraitement / chunking / provenance | ✅ | Paragraphes de 300 mots, recouvrement 20 % (choix du notebook 09) ; `doc_id`, titre, auteurs, section, `chunk_id`. **Pas de numéro de page.** |
| Dataset | ✅ / ⚠️ | 5 jeux publics (SciFact, TREC-COVID, NFCorpus, SciDocs, LitSearch) ; 261 questions sur 80 articles (notebook 09). L'évaluation du RAG de l'app n'utilise que 5 questions (`rag/eval/eval_questions.json`). |
| Baselines | ✅ | TF-IDF, BM25 classique, BM25 optimisé sur les 5 jeux (`results/metrics.csv`, notebook 07). |
| ML | ❌ | LogReg / SVM / Random Forest codés (notebooks 03 et 11), **aucun résultat sauvegardé**. |
| DL / Transfer Learning | ✅ | Notebook 10 : MiniLM-L6, SciBERT, SPECTER2, mE5-base, mE5-large, BGE-M3, seuls et en hybride avec BM25, test de Wilcoxon + correction de Holm. |
| Fine-Tuning | ❌ | Notebooks 04_05 (cross-encodeurs) et 06bis (GPL) écrits, **aucun résultat ni modèle sauvegardé**. |
| Évaluation / comparaison | ⚠️ | nDCG@10, Recall@100, MRR@10, P@5, latence. Manquent : taille, mémoire, coût ; lignes ML et fine-tuné. |
| Sélection → intégration | ⚠️ | L'app utilise `intfloat/multilingual-e5-small` + `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (`rag/recherche.py`). **e5-small ne fait pas partie de la comparaison du notebook 10.** |
| RAG | ✅ / ⚠️ | Hybride → reranker → qwen2.5:3b → vérification → réponse + citations (lien vers le PDF). Manque la reformulation de la requête ; vérification par simple recouvrement lexical (`SEUIL_COUVERTURE = 0.10`). |
| Knowledge Graph | ❌ | Page « Coming soon », pas de Neo4j. |
| Research Twin | ⚠️ | Projet avec titre, problématique, question, objectifs, hypothèses. Page Twin « Coming soon ». |
| Agents | ❌ | Rien, pas de LangGraph. |
| SaaS / infra | ⚠️ | Next.js, FastAPI, Supabase Auth, Postgres (docker-compose), isolation utilisateur. Absents : Qdrant, Neo4j, Redis, CI GitHub Actions. Index reconstruit en mémoire à chaque démarrage. |

### Dettes techniques relevées pendant l'intégration

- **Deux copies de la recherche hybride** : `rag/recherche.py` (articles) et `backend/app/services/video/search.py` (vidéos).
- **`SourceType` ne contient que `video`** (`backend/app/models/source.py`) : les articles ne sont pas des sources en base, ils passent par `app/services/papers.py` + `rag_corpus.py`.
- **`rag.search()` interroge tout le corpus**, sans filtre par document ni par utilisateur.
- **Environnement GPU fragile** : torch `2.6.0+cu124` est installé à la main alors que `uv.lock` référence `2.15.0` CPU ; `.claude/launch.json` lance le backend avec `uv run --no-sync` pour ne pas l'écraser.
- **Clé HMAC des liens vidéo de 31 octets** (minimum recommandé : 32) — avertissement `InsecureKeyLengthWarning`.
- **Ingestion en `BackgroundTasks` FastAPI** : pas de file de tâches, pas de reprise après redémarrage.

---

## 2. Principes de correction

1. **Un seul schéma de chunk** pour tous les types de source (cahier, section 10.3) :
   `document_id, source_type, title, authors, date, chunk_id, page | timestamp, section, content`.
2. **Un seul module de retrieval** partagé par le RAG articles, le RAG vidéo et `/search`.
3. **Embeddings calculés une fois à l'ingestion**, stockés dans Qdrant ; jamais recalculés au démarrage.
4. **Le modèle intégré est celui choisi par le protocole** (section 20), avec une décision écrite.
5. **Chaque expérience est tracée** dans `results/metrics.csv` : hypothèse, méthode, paramètres, métriques, analyse.
6. **Isolation par utilisateur** sur toutes les sources personnelles (cahier, section 36).

---

## 3. Phases

Ordre : phases 1 à 6 = **P0 (obligatoire MVP)**, phases 7 à 9 = **P1 (MVP étendu)**, phase 10 = transversale.

### Phase 1 — Socle de données et ingestion multimodale (P0)

**Objectif** : importer les 5 types de source depuis l'interface et les ramener au schéma commun.

- [ ] **1.1 Modèle unifié** — étendre `SourceType` à `pdf, web, figure, video, personal` ; ajouter à `Chunk` les champs `page`, `section`, `authors`, `date`. Migration Alembic (remplace `init_db()`).
- [ ] **1.2 Corpus arXiv en base** — importer les 139 articles de `data_latex/data/index/documents.jsonl` comme sources partagées (lecture seule), avec leurs chunks. Supprime le pseudo-document `corpus-arxiv`.
- [ ] **1.3 PDF** — extraction texte (PyMuPDF), suppression en-têtes / pieds de page, détection de structure (Title, Abstract, Introduction, Methodology, Dataset, Experiments, Results, Conclusion — cahier, section 12), **numéro de page par chunk**.
- [ ] **1.4 Web** — URL → téléchargement → extraction du contenu principal → métadonnées → chunking.
- [ ] **1.5 Images / figures** — OCR + description par un modèle vision local → texte indexable, lié à l'image source.
- [ ] **1.6 YouTube par URL** — récupération de l'audio puis pipeline de transcription existant (`services/video/transcription.py`). Vérifier les conditions d'utilisation de YouTube et la licence des vidéos ; l'outil de téléchargement est à installer avec accord.
- [ ] **1.7 Documents personnels** — `.docx`, `.txt`, `.md` → extraction → chunking, visibles uniquement par leur propriétaire.
- [ ] **1.8 Chunking commun** — texte : paragraphe, 300 mots, recouvrement 20 % (notebook 09) ; vidéo : 45 s / 200 mots (existant).

**Critères d'acceptation** : chaque type s'importe depuis la page Sources, passe par les statuts `pending → … → ready`, produit des chunks avec provenance complète ; tests d'API par type ; un utilisateur ne voit jamais les sources personnelles d'un autre.

### Phase 2 — Index persistant (P0)

- [ ] **2.1** Ajouter Qdrant au `docker-compose.yml` ; une collection, payload = schéma de chunk + `user_id`.
- [ ] **2.2** Embeddings écrits dans Qdrant à l'ingestion (phase 1), plus de reconstruction au démarrage.
- [ ] **2.3** Partie lexicale persistée (index BM25 sérialisé ou vecteurs creux Qdrant).
- [ ] **2.4** Filtres par `user_id`, `document_id`, `source_type`, `project_id` dans `search()`.

**Critères** : premier `/answer` après redémarrage sans phase d'indexation ; recherche limitée à une source choisie.

### Phase 3 — Protocole expérimental complet (P0)

Dépôt : `ResearchMind1/ResearchMind-AI`. Sortie : lignes ajoutées à `results/metrics.csv`.

- [ ] **3.1 Dataset ResearchMind** — partir des 261 questions du notebook 09 ; format `query / passage / label` (cahier, section 13) ; découpage train / validation / test documenté ; ajouter des questions en français (le corpus est en anglais, les utilisateurs posent en français).
- [ ] **3.2 Baselines** — fait (notebook 07). Les réévaluer sur le dataset ResearchMind.
- [ ] **3.3 Machine Learning** — exécuter le notebook 11 (LogReg, SVM, Random Forest en reranking) et sauvegarder ses résultats.
- [ ] **3.4 DL / Transfer Learning** — fait (notebook 10). **Ajouter `multilingual-e5-small` et le reranker `mmarco-mMiniLMv2`** (les modèles réellement intégrés) à la comparaison.
- [ ] **3.5 Fine-Tuning** — exécuter le notebook 04_05 (cross-encodeur) et/ou 06bis (GPL) ; sauvegarder le modèle dans `models/` et ses résultats.
- [ ] **3.6 Évaluation** — compléter le tableau de la section 21 : MRR, Recall@k, nDCG@k, **latence, taille, mémoire (VRAM, GPU GTX 1650 de 4 Go), coût** ; tests de significativité.
- [ ] **3.7 Sélection** — décision écrite (`docs/decision_modele.md`) : compromis qualité de retrieval + performance système + contraintes SaaS (cahier, section 22.2).

**Critères** : chaque ligne du tableau de la section 21 a une mesure réelle ; chaque modèle a hypothèse, méthode, paramètres, métriques et analyse (section 20).

### Phase 4 — Intégration du modèle sélectionné (P0)

- [ ] **4.1** Fusionner `rag/recherche.py` et `services/video/search.py` en un module unique `backend/app/services/retrieval/`.
- [ ] **4.2** Noms des modèles (embedding, reranker) dans la configuration, fixés par la décision 3.7 ; reranker fine-tuné chargé depuis `models/` si sélectionné.
- [ ] **4.3** Test de non-régression : petit jeu d'évaluation rejoué en CI, seuil minimal de nDCG.

**Critères** : un seul code de recherche ; le modèle en production est celui de `decision_modele.md`.

### Phase 5 — RAG complet (P0)

Parcours du cahier (section 24) : `Question → Query Understanding → Hybrid Retrieval → Reranking → Top-K Evidence → LLM → Verification → Answer → Citations`.

- [ ] **5.1 Query Understanding** — reformulation et traduction FR → EN avant la recherche (déjà présent dans le prototype vidéo `D:\Transcription\rag.py`, absent de `rag/`).
- [ ] **5.2 Vérification renforcée** — vérifier chaque phrase de la réponse contre les passages (second appel LLM de vérification, comme `services/video/qa.py`) au lieu du seul recouvrement lexical.
- [ ] **5.3 Calibrage** — recalibrer le plancher et le seuil sur un jeu incluant des **questions hors sujet** (non testé aujourd'hui).
- [ ] **5.4 Citations précises** — page (PDF), timestamp (vidéo), image (figure) ; ouverture du PDF à la bonne page.
- [ ] **5.5 Évaluation** — ROUGE + fidélité de la réponse sur le jeu de test 3.1 (plus seulement 5 questions).

**Critères** : les questions types de la section 25 (méthode, dataset, résultats, limitations, méthodes comparées) obtiennent une réponse citée ou un refus explicite.

### Phase 6 — Interface SaaS (P0)

- [ ] **6.1** Import des 5 types de source depuis la page Sources.
- [ ] **6.2** Bibliothèque étendue aux documents de l'utilisateur (aujourd'hui : 139 articles arXiv).
- [ ] **6.3** Page Recherche branchée sur `POST /search` (la route existe, pas d'écran).
- [ ] **6.4** Visionneuse : PDF à la page citée, vidéo au timestamp (fait), figure avec sa description.

**Critères** : le parcours de la section 40 (étapes 1 à 12) est réalisable dans l'interface.

### Phase 7 — Research Twin v1 (P1)

- [ ] **7.1** Étendre `Project` : méthodes, données, expériences, résultats, références, limitations, research gaps (cahier, section 28).
- [ ] **7.2** Rattacher sources et réponses au projet (`project_id` existe déjà sur les sources).
- [ ] **7.3** Mise à jour uniquement à partir d'informations **ajoutées ou validées par l'utilisateur** (section 8.1.7) : bouton « ajouter au Twin » sur une réponse ou une citation.
- [ ] **7.4** Page Research Twin (remplace « Coming soon »).

### Phase 8 — Knowledge Graph v1 (P1)

- [ ] **8.1** Neo4j dans `docker-compose.yml`.
- [ ] **8.2** Nœuds `Paper`, `Author` et relation `AUTHORED` depuis `documents.jsonl` (données déjà disponibles).
- [ ] **8.3** Relation `CITES` depuis les fichiers `.bib` des articles (champ `bib_files` de `documents.jsonl`).
- [ ] **8.4** Nœuds `Method`, `Dataset`, `Concept`, `Result` et relations `USES`, `PROPOSES`, `EVALUATES`, `APPLIED_TO` extraits par LLM, **avec validation**.
- [ ] **8.5** Page Knowledge Graph (vue navigable).

### Phase 9 — Agents (P1 : Video et Vision Agent ; P2 : le reste)

- [ ] **9.1** LangGraph ; un agent seulement si la décomposition apporte une valeur mesurable (cahier, section 32).
- [ ] **9.2** Video Agent et Vision Agent, au-dessus des pipelines des phases 1 et 5.
- [ ] **9.3** Verification Agent (réutilise 5.2), puis Research Twin Agent (réutilise 7.3).

### Phase 10 — Infrastructure et qualité (transversale)

- [ ] **10.1 GPU reproductible** — déclarer l'index PyTorch CUDA dans `backend/pyproject.toml` (`[tool.uv.sources]`) pour que `uv sync` installe la bonne version ; retirer `--no-sync` de `.claude/launch.json`.
- [ ] **10.2 Redis + file de tâches** pour l'ingestion (remplace `BackgroundTasks`).
- [ ] **10.3 docker-compose complet** : db, qdrant, neo4j, redis, backend, frontend, ollama.
- [ ] **10.4 CI GitHub Actions** : `pytest`, `tsc --noEmit`, lint, test de non-régression 4.3.
- [ ] **10.5 Sécurité** (section 36) : clé HMAC ≥ 32 octets, limitation des requêtes, journalisation, validation des entrées, sauvegardes.
- [ ] **10.6 Documentation** : architecture, modèles, contrat d'API à jour.

---

## 4. Dépendances

```
Phase 1 ──► Phase 2 ──► Phase 4 ──► Phase 5 ──► Phase 6
              ▲            ▲
Phase 3 ──────┘ (3.1) ─────┘ (3.7 décision)
Phase 1 + 5 ──► Phase 7 (Twin) ──► Phase 9 (agents)
Phase 1 ──► Phase 8 (Knowledge Graph)
Phase 10 : en continu
```

Points de départ sans dépendance : **3.4 + 3.7** (corriger l'incohérence du modèle intégré), **3.3 et 3.5** (exécuter les notebooks existants), **8.2** (données déjà disponibles).

## 5. Correspondance avec les critères de réussite du MVP (cahier, section 40)

| Étape du parcours MVP | Phase |
|---|---|
| 1. Création du projet | fait |
| 2. Import d'une source (PDF / Web / Image / Vidéo / document personnel) | 1, 6 |
| 3. Extraction (+ OCR / transcription) | 1 |
| 4. Nettoyage / chunking | 1 |
| 5. Indexation | 2 |
| 6 à 9. Question, retrieval, reranking, sélection des preuves | 4, 5 |
| 10. Génération RAG | 5 |
| 11 et 12. Affichage de la réponse et des citations | fait, à compléter en 5.4 |
| 13. Mise à jour du Research Twin | 7 |
| 14. Représentation des relations principales | 8 |

## 6. Livrables (cahier, section 42)

| Livrable | État |
|---|---|
| Pipeline d'ingestion multimodale | partiel → phase 1 |
| Pipeline de préparation des données | partiel → phase 1 |
| Dataset | partiel → 3.1 |
| Notebooks d'expérimentation | écrits ; 03, 04_05, 06bis, 11 sans résultats → 3.3, 3.5 |
| Modèles ML / DL / TL / Fine-Tuning | DL et TL faits ; ML et Fine-Tuning → 3.3, 3.5 |
| Rapport d'évaluation, modèle final sélectionné | → 3.6, 3.7 |
| Pipeline Retrieval / RAG | fait, à compléter → 4, 5 |
| Knowledge Graph | → 8 |
| Research Twin | → 7 |
| Architecture agentique (Vision Agent, Video Agent) | → 9 |
| API FastAPI, application Next.js | faits, à étendre → 6 |
| Tests | 53 tests backend ; CI → 10.4 |
| Dockerisation | partielle → 10.3 |
