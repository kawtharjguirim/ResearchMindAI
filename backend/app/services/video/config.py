"""
Paramètres du module vidéo, repris du prototype (D:\\Transcription).

Décisions figées : LLM qwen2.5:3b uniquement, mode extractif, règle de décision
combinée (plancher 0,02 + seuil 0,07). Les chemins et l'adresse d'Ollama peuvent
être changés par variables d'environnement, sans toucher à app/core/config.py.
"""
import os
from pathlib import Path

# ---------- Stockage local (ignoré par git : backend/storage/.gitignore) ----------
BACKEND_DIR = Path(__file__).resolve().parents[3]
STORAGE_DIR = Path(os.getenv("VIDEO_STORAGE_DIR", BACKEND_DIR / "storage"))
VIDEOS_DIR = STORAGE_DIR / "videos"
EXT_VIDEO = (".mp4", ".webm", ".mkv", ".mov", ".m4v")
TAILLE_MAX_VIDEO = int(os.getenv("VIDEO_MAX_BYTES", 2 * 1024**3))   # 2 Go
# Paquets du groupe uv « video » (uv sync --group video), absents de l'image Docker par défaut
DEPENDANCES = ("faster_whisper", "sentence_transformers", "rank_bm25", "numpy")

# ---------- Transcription (faster-whisper) ----------
WHISPER_MODEL_DIR = os.getenv("WHISPER_MODEL_DIR", str(STORAGE_DIR / "models" / "whisper"))
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")              # "cuda" ou "cpu"
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8_float16")  # "int8" sur CPU
CUDA_DLL_DIR = os.getenv("CUDA_DLL_DIR", "")   # Windows : dossier des DLL cuBLAS 12 / cuDNN 9
WHISPER_PROMPT = ("Transformer, BERT, SciBERT, embeddings, BM25, RAG, "
                  "fine-tuning, nDCG, retrieval, LangGraph")

# ---------- Découpage ----------
MAX_SECONDES = 45     # durée maximale d'un chunk
MAX_MOTS = 200        # nombre maximal de mots d'un chunk
CHEVAUCHEMENT = 1     # segments repris au début du chunk suivant

# ---------- Recherche ----------
MODELE_E5 = "intfloat/multilingual-e5-small"
MODELE_RERANKER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
N_CANDIDATS = 10      # candidats envoyés au reranker
RRF_K = 60

# ---------- LLM (Ollama) ----------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODELE_LLM = "qwen2.5:3b"   # tient entièrement dans les 4 Go de la GTX 1650
OPTIONS_LLM = {"temperature": 0, "seed": 42, "num_ctx": 4096}
TIMEOUT_LLM = 900

# ---------- Questions-réponses (mode extractif) ----------
TOP_K = 3                 # passages lus par la vérification
SEUIL_PREUVE = 0.5        # part des mots de la phrase-preuve présents dans l'extrait
SEUIL_INCLUSE = 0.9       # copie longue : part des mots d'une phrase présents dans la copie du LLM
# Règle combinée. ATTENTION : valeurs ajustées sur une seule vidéo
# (eval_questions_dur.json) ; à valider sur d'autres vidéos.
SEUIL_RERANK = 0.07       # LLM « non » et rerank max >= seuil -> confiance faible
PLANCHER_RERANK = 0.02    # rerank max < plancher -> hors sujet, même si le LLM dit « oui »

LANGUES = {"fr": "français", "en": "anglais", "es": "espagnol", "de": "allemand"}

# Mots tolérés dans une reformulation même s'ils ne sont pas dans la citation
MOTS_LIBRES = set("""video selon explique indique dit affirme precise raconte auteur narrateur
citation passage extrait partiellement seulement aussi donc ainsi""".split())

MSG_HORS_SUJET = ("La vidéo ne contient pas la réponse à cette question. "
                  "Les passages les plus proches abordent un thème voisin, sans y répondre.")
MSG_CONFIANCE_FAIBLE = "Confiance faible, à vérifier"
MSG_SANS_CITATION = ("Aucune phrase des passages ne donne clairement la réponse : "
                     "vérifie les passages ci-dessous.")
