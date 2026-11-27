"""
Paramètres du module vidéo, repris du prototype (D:\\Transcription).

Décisions figées : LLM qwen2.5:3b uniquement, mode extractif, règle de décision
combinée (plancher 0,02 + seuil 0,07). Les chemins et l'adresse d'Ollama se règlent
dans backend/.env ou par variables d'environnement (prioritaires), sans toucher à
app/core/config.py. Voir backend/.env.example.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[3]


class _VideoEnv(BaseSettings):
    """Réglages locaux du module vidéo, lus dans backend/.env puis l'environnement."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    video_storage_dir: str = str(BACKEND_DIR / "storage")
    video_max_bytes: int = 2 * 1024**3        # 2 Go
    whisper_model_dir: str = ""               # vide : <stockage>/models/whisper
    whisper_device: str = "cuda"              # "cuda" ou "cpu"
    whisper_compute_type: str = "int8_float16"  # "int8" sur CPU
    cuda_dll_dir: str = ""                    # Windows : dossier des DLL cuBLAS 12 / cuDNN 9
    ollama_url: str = "http://localhost:11434"


_env = _VideoEnv()

# ---------- Stockage local (ignoré par git : backend/storage/.gitignore) ----------
STORAGE_DIR = Path(_env.video_storage_dir)
VIDEOS_DIR = STORAGE_DIR / "videos"
EXT_VIDEO = (".mp4", ".webm", ".mkv", ".mov", ".m4v")
TAILLE_MAX_VIDEO = _env.video_max_bytes
# Paquets du groupe uv « video » (uv sync --group video), absents de l'image Docker par défaut
DEPENDANCES = ("faster_whisper", "sentence_transformers", "nltk", "sklearn", "scipy", "numpy")

# ---------- Transcription (faster-whisper) ----------
WHISPER_MODEL_DIR = _env.whisper_model_dir or str(STORAGE_DIR / "models" / "whisper")
WHISPER_DEVICE = _env.whisper_device
WHISPER_COMPUTE_TYPE = _env.whisper_compute_type
CUDA_DLL_DIR = _env.cuda_dll_dir
WHISPER_PROMPT = ("Transformer, BERT, SciBERT, embeddings, BM25, RAG, "
                  "fine-tuning, nDCG, retrieval, LangGraph")

# ---------- Découpage ----------
MAX_SECONDES = 45     # durée maximale d'un chunk
MAX_MOTS = 200        # nombre maximal de mots d'un chunk
CHEVAUCHEMENT = 1     # segments repris au début du chunk suivant

# ---------- Recherche ----------
# Modèles, fusion et reranker : moteur commun, voir rag/config_recherche.json et search.py.

# Pages web : le reranker donne des scores bien plus hauts (0,41 à 1,00 pour les passages
# pertinents d'une page Wikipédia). Seuils calibrés sur cette seule page : à valider sur d'autres.
SEUIL_RERANK_WEB = 0.5
PLANCHER_RERANK_WEB = 0.1

# PDF : les scores du reranker sont bien plus bas sur un article scientifique en anglais
# (0,10 au mieux pour le bon passage). Valeurs à valider sur d'autres PDF.
SEUIL_RERANK_PDF = 0.005
PLANCHER_RERANK_PDF = 0.001

# ---------- LLM (Ollama) ----------
OLLAMA_URL = _env.ollama_url
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

MSG_HORS_SUJET = ("The source does not contain the answer to this question. "
                  "The closest passages cover a related topic without answering it.")
MSG_CONFIANCE_FAIBLE = "Low confidence, please verify"
MSG_SANS_CITATION = ("No passage sentence clearly gives the answer: "
                     "check the passages below.")
