# Guide d'utilisation — ResearchMind AI (état au 14/11/2026)

Ce guide explique comment installer, lancer et utiliser le projet **tel qu'il est aujourd'hui**
sur la branche `Mohamed`. Il décrit aussi ce qui ne fonctionne pas encore.

---

## 1. Vue d'ensemble

| Partie | Rôle | Technologie | Port |
|---|---|---|---|
| `frontend/` | Interface web | Next.js 15, TypeScript, Tailwind | 3000 |
| `backend/` | API, authentification, vidéos, pont vers le RAG | FastAPI, SQLAlchemy | 8000 |
| `rag/` | Recherche hybride et réponses sur le corpus arXiv | sentence-transformers, nltk, scikit-learn | — |
| `data_latex/` | Corpus : 139 articles arXiv (`.tex` + PDF) | — | — |
| Ollama (externe) | LLM local qwen2.5:3b pour générer les réponses | Ollama | 11434 |
| Supabase (externe) | Comptes utilisateurs et connexion | Supabase Auth | — |

---

## 2. Prérequis à installer

| Outil | Version | Pourquoi | Vérifier |
|---|---|---|---|
| Git | récent | récupérer le dépôt | `git --version` |
| Python | 3.12 ou plus | backend et RAG | `python --version` |
| uv | récent | gestion de l'environnement Python | `uv --version` |
| Node.js + npm | 20 ou plus | frontend | `node --version` |
| Ollama | récent | LLM local | `ollama --version` |
| Pilote NVIDIA (facultatif) | compatible CUDA 12 | accélérer les calculs (GTX 1650 testée) | `nvidia-smi` |
| Docker (facultatif) | récent | PostgreSQL ; sinon SQLite suffit | `docker --version` |

Installer uv :

```bash
pip install uv
```

Télécharger le modèle de langue (environ 2 Go, une seule fois) :

```bash
ollama pull qwen2.5:3b
```

---

## 3. Récupérer le projet

```bash
git clone https://github.com/kawtharjguirim/ResearchMindAI.git
```

```bash
cd ResearchMindAI
```

```bash
git checkout Mohamed
```

---

## 4. Supabase (une seule fois)

1. Créer un projet sur supabase.com.
2. **Authentication → URL Configuration** : Site URL `http://localhost:3000`, et ajouter la Redirect URL `http://localhost:3000/auth/callback`.
3. **Project Settings → API** : copier l'URL du projet et la clé `anon`.
4. Si le projet utilise l'ancien secret JWT : le copier aussi (sinon, laisser vide).

> Si le projet Supabase est **en pause** (inactif plusieurs jours), la connexion échoue : le réactiver depuis le tableau de bord Supabase.

---

## 5. Installer et configurer le backend

```bash
cd backend
```

Installer les dépendances (y compris le groupe `video`, nécessaire au RAG) :

```bash
uv sync --group video --group dev
```

Créer le fichier de configuration puis le remplir :

```bash
cp .env.example .env
```

Variables principales de `backend/.env` :

| Variable | Valeur |
|---|---|
| `SUPABASE_URL` | URL du projet Supabase |
| `SUPABASE_JWT_SECRET` | secret JWT (seulement pour l'ancien mode HS256), **32 caractères minimum conseillés** |
| `WHISPER_MODEL_DIR` | dossier du modèle faster-whisper (transcription vidéo) |
| `CUDA_DLL_DIR` | Windows + GPU NVIDIA : dossier des DLL CUDA pour faster-whisper |
| `WHISPER_DEVICE` | `cuda` ou `cpu` |
| `OLLAMA_URL` | `http://localhost:11434` (par défaut) |

Sans base PostgreSQL, le backend utilise SQLite automatiquement.

### 5.1 Utiliser le GPU (facultatif, fortement conseillé)

`uv sync` installe PyTorch **CPU**. Pour le GPU, installer la version CUDA **après** le `uv sync` :

```bash
uv pip install torch --index-url https://download.pytorch.org/whl/cu124 --python .venv/Scripts/python.exe --reinstall-package torch
```

Vérifier :

```bash
.venv/Scripts/python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Résultat attendu : `2.6.0+cu124 True`.

> **Attention** : tout nouveau `uv sync` (ou `uv run` sans `--no-sync`) réinstalle la version CPU. Il faut alors relancer la commande ci-dessus. C'est pour cela que le backend est lancé avec `uv run --no-sync`.

---

## 6. Préparer le corpus RAG (une seule fois)

Les passages et les embeddings ne sont pas dans git (fichiers lourds, régénérables).

Découper les 139 articles en passages (quelques secondes) :

```bash
cd rag
```

```bash
../backend/.venv/Scripts/python.exe -I chunking.py --out data/chunks.jsonl
```

Résultat attendu : `3867 chunks (3867 article, 0 video)`.

Calculer les embeddings une première fois (environ 12 min sur GTX 1650, beaucoup plus sur CPU ; le modèle mE5-base, environ 1 Go, est téléchargé au premier lancement) :

```bash
../backend/.venv/Scripts/python.exe -I rag.py "Comment TERMinator représente-t-il les acides aminés ?"
```

Les embeddings sont alors mis en cache dans `rag/data/cache/` : les lancements suivants prennent environ 30 secondes.

---

## 7. Installer et configurer le frontend

```bash
cd frontend
```

```bash
npm install
```

```bash
cp .env.example .env.local
```

Remplir `frontend/.env.local` :

| Variable | Valeur |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL du projet Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clé `anon` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

---

## 8. Lancer l'application

Trois programmes doivent tourner en même temps (un terminal chacun).

**Ollama** (souvent déjà lancé en arrière-plan sous Windows) :

```bash
ollama serve
```

**Backend** (depuis `backend/`) :

```bash
uv run --no-sync --group video uvicorn app.main:app --port 8000
```

**Frontend** (depuis `frontend/`) :

```bash
npm run dev
```

Ouvrir http://localhost:3000, créer un compte puis se connecter.
Documentation de l'API : http://localhost:8000/docs.

> Faire l'inscription et la confirmation d'e-mail **dans le même navigateur** : sinon la connexion par lien échoue (code PKCE stocké dans l'autre navigateur).

---

## 9. Utiliser l'application

| Page (barre latérale) | Ce qu'on peut faire |
|---|---|
| **My projects** | Créer un projet de recherche (titre, problématique, question, objectifs, hypothèses). |
| **Research assistant** | Choisir une source (une vidéo ou « Corpus arXiv (data_latex) ») et poser une question en français. La réponse cite les passages ; un clic ouvre la vidéo au bon moment ou l'article PDF. |
| **Sources** | Importer une vidéo (`.mp4`, `.webm`, `.mkv`, `.mov`, `.m4v`) : elle est transcrite puis indexée. Un clic sur une vidéo prête ouvre le lecteur avec la transcription synchronisée. |
| **Library** | Parcourir les 139 articles du corpus : recherche, filtres par domaine, tri, puis lecture du PDF. |
| **Evaluation set** | Relire les 118 questions de test : valider, corriger ou rejeter chacune. |
| Research Twin, Knowledge Graph | Pas encore développés (« Coming soon »). |

**Temps de réponse** : la première question sur le corpus après un redémarrage du backend prend environ 30 secondes (chargement des modèles), les suivantes quelques secondes de recherche plus la génération par Ollama.

---

## 10. Commandes utiles (évaluation et tests)

Depuis `rag/` :

| Commande | Rôle |
|---|---|
| `../backend/.venv/Scripts/python.exe -I parite.py` | Vérifie que le moteur reproduit le notebook 10 (nécessite le dépôt d'expérimentation `ResearchMind1/ResearchMind-AI` à côté du projet). |
| `../backend/.venv/Scripts/python.exe -I evaluation_corpus.py` | Évalue la recherche sur les questions **validées** du jeu de test. |
| `../backend/.venv/Scripts/python.exe -I evaluation_corpus.py --split tout --toutes` | Même chose sur toutes les questions, validées ou non. |

Tests backend (depuis `backend/`) :

```bash
uv run --no-sync pytest
```

Vérification TypeScript (depuis `frontend/`) :

```bash
npx tsc --noEmit
```

---

## 11. État actuel du projet

**Fonctionne :**
- Comptes et connexion (Supabase), projets de recherche, isolation des données par utilisateur.
- Vidéos : import, transcription, recherche, réponses avec horodatage, lecteur synchronisé.
- Corpus arXiv : 139 articles, recherche hybride (BM25 + mE5-base + fusion RRF + reranker), réponses citées, bibliothèque et visionneuse PDF.
- Moteur identique au système évalué au notebook 10 (test de parité réussi).
- Jeu de test de 118 questions et page de relecture.
- 57 tests backend, TypeScript sans erreur.

**Limites connues :**
- Les 118 questions de test ne sont pas encore relues : les résultats d'évaluation restent provisoires.
- Sur notre corpus, E5 seul semble meilleur que la fusion avec BM25 (questions en français, corpus en anglais) : à confirmer après relecture.
- Le reranker n'a pas été sélectionné par une expérience (notebook 11 pas encore exécuté) ; le fine-tuning (notebook 04_05) non plus.
- Le module vidéo utilise encore l'ancien modèle e5-small.
- Pas encore d'import PDF, Web, images ni YouTube dans l'application ; pas de Knowledge Graph, de Research Twin complet ni d'agents.
- Le PDF s'ouvre au début, pas à la page du passage cité (les passages viennent du `.tex`, sans numéro de page).

Le détail de ce qui reste à faire est dans [`docs/plan_integration_pipeline.md`](plan_integration_pipeline.md).

---

## 12. Problèmes fréquents

| Symptôme | Solution |
|---|---|
| « Cannot reach the API » | Le backend n'est pas lancé, ou `NEXT_PUBLIC_API_URL` est faux. |
| La connexion échoue | Projet Supabase en pause, ou inscription faite dans un autre navigateur. |
| Les réponses donnent une erreur 503 | Ollama n'est pas lancé, ou `qwen2.5:3b` n'est pas téléchargé. |
| Le corpus arXiv donne des réponses « simulées » | `rag/data/chunks.jsonl` manque : refaire l'étape 6. |
| La première question est très lente | Normal la toute première fois (calcul des embeddings) ; ensuite le cache est utilisé. |
| Le GPU n'est plus utilisé | Un `uv sync` a réinstallé torch CPU : refaire l'étape 5.1. |
| Mémoire GPU saturée (4 Go) | Le backend et Ollama partagent le GPU : fermer les autres programmes qui l'utilisent. |
