import pytest

from app.services import rag_corpus


@pytest.fixture(autouse=True)
def corpus_simule(monkeypatch):
    """Mode simulé par défaut, même si rag/data/chunks.jsonl existe sur la machine : sinon les
    tests construiraient le vrai index et appelleraient Ollama. Le fixture real_corpus le réactive."""
    monkeypatch.setattr(rag_corpus, "disponible", lambda: False)
