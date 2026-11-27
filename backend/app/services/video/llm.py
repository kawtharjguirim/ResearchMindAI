"""Client minimal d'Ollama (/api/chat), limité à qwen2.5:3b."""
import json
import urllib.error
import urllib.request

from .config import MODELE_LLM, OLLAMA_URL, OPTIONS_LLM, TIMEOUT_LLM


class OllamaIndisponible(RuntimeError):
    pass


def chat(messages: list[dict], schema: dict | None = None, appels: list | None = None,
         etape: str | None = None):
    """
    Appel non streamé ; avec un schéma JSON, renvoie le dict décodé, sinon le texte.
    Si `appels` est une liste, y ajoute les durées mesurées par Ollama.
    """
    corps = {"model": MODELE_LLM, "messages": messages, "stream": False,
             "options": OPTIONS_LLM, "keep_alive": "30m"}
    if schema:
        corps["format"] = schema
    req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=json.dumps(corps).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_LLM) as r:
            rep = json.loads(r.read())
    except urllib.error.URLError as e:
        raise OllamaIndisponible(f"Ollama injoignable sur {OLLAMA_URL} ({e}).") from e
    if appels is not None:
        appels.append({"etape": etape,
                       "chargement_s": rep.get("load_duration", 0) / 1e9,
                       "prompt_s": rep.get("prompt_eval_duration", 0) / 1e9,
                       "generation_s": rep.get("eval_duration", 0) / 1e9,
                       "tokens_generes": rep.get("eval_count", 0)})
    contenu = rep["message"]["content"]
    return json.loads(contenu) if schema else contenu.strip()


def verifier_modele() -> None:
    """Lève OllamaIndisponible si Ollama ne répond pas ou si qwen2.5:3b n'est pas installé."""
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5) as r:
            noms = [m["name"] for m in json.loads(r.read())["models"]]
    except urllib.error.URLError as e:
        raise OllamaIndisponible(f"Ollama injoignable sur {OLLAMA_URL} ({e}).") from e
    if MODELE_LLM not in noms:
        raise OllamaIndisponible(f"{MODELE_LLM} absent d'Ollama : lance « ollama pull {MODELE_LLM} ».")
