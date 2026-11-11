"""RAG minimal : search() et answer(), contrat documente dans docs/contrat_api.md.

LLM : qwen2.5:3b uniquement, via Ollama local (http://localhost:11434). Regle de
verification : la reponse n'est "verifiee" que si le meilleur score de reranking
depasse PLANCHER_RERANK ET qu'au moins un des extraits fournis recouvre lexicalement
la reponse au-dessus de SEUIL_COUVERTURE (fonction `couverture`, reprise de
backend/app/services/video/text.py -- lecture seule, backend/ n'est pas modifie).

Ancienne version : la citation etait detectee en cherchant "[1]", "[2]"... litteralement
dans le texte genere. qwen2.5:3b ne reprend quasiment jamais ce format (verifie=False sur
toutes les reponses testees, meme correctes), d'ou le recouvrement lexical a la place --
plus robuste au format de sortie du LLM.

Limite connue (voir le rapport de fin de mission) : pas de reecriture de requete, pas
de verification par un second appel LLM separe, pas de mode extractif -- une seule
passe de generation avec citations, plus simple que D:\\Transcription\\rag.py.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # utile avec python -I
from recherche import N_CANDIDATS, Index, normaliser  # noqa: E402

MODELE_LLM = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434"
PLANCHER_RERANK = 0.02   # sous ce score, aucun passage n'est juge pertinent
SEUIL_COUVERTURE = 0.10  # recouvrement lexical minimal reponse/passage pour citer un extrait ;
                         # seuil bas car les articles sont en anglais et les reponses en francais :
                         # le recouvrement vient surtout des termes techniques et noms propres
                         # partages, jamais d'une traduction mot a mot (calibre empiriquement,
                         # voir le rapport de fin de mission)


def couverture(phrase, texte):
    """Part des mots (normalises) de `phrase` presents dans `texte` (1.0 = recopiee).
    Repris de backend/app/services/video/text.py (lecture seule), avec notre normaliser()."""
    mots = normaliser(phrase)
    vus = set(normaliser(texte))
    return sum(m in vus for m in mots) / len(mots) if mots else 0.0

_index = None  # Index charge une seule fois par processus (chargement paresseux)


def charger_index(chemin_chunks=None):
    """Charge (une seule fois) l'Index a partir de rag/data/chunks.jsonl, ou du chemin donne."""
    global _index
    if _index is None:
        chemin = Path(chemin_chunks or Path(__file__).resolve().parent / "data" / "chunks.jsonl")
        with open(chemin, encoding="utf-8") as f:
            chunks = [json.loads(l) for l in f]
        _index = Index(chunks)
    return _index


def search(query, top_k=5):
    """Les top_k passages les plus pertinents (BM25+E5 -> RRF -> reranker). Voir contrat_api.md."""
    index = charger_index()
    resultats = index.rechercher(query, n=max(top_k, N_CANDIDATS))
    sortie = []
    for r in resultats[:top_k]:
        c = r["chunk"]
        item = {"chunk_id": c["chunk_id"], "document_id": c["document_id"],
                "source": c["source"], "text": c["text"], "score": round(r["rerank"], 4)}
        if c["source"] == "video":
            item["timestamp"] = c.get("timestamp")
        sortie.append(item)
    return sortie


def _appeler_ollama(prompt, num_predict=200, timeout=900):
    # num_predict borne la longueur de la reponse : generation tres lente en CPU sur cette
    # machine (environ 9 s/jeton observes avec qwen2.5:3b), d'ou le timeout genereux.
    corps = json.dumps({"model": MODELE_LLM, "prompt": prompt, "stream": False,
                        "options": {"temperature": 0, "seed": 42, "num_predict": num_predict}}
                       ).encode("utf-8")
    requete = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=corps,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        return json.loads(reponse.read())["response"].strip()


def answer(query, top_k=5):
    """Reponse de qwen2.5:3b a partir des passages de search(), avec citations. Voir contrat_api.md."""
    passages = search(query, top_k)
    if not passages or passages[0]["score"] < PLANCHER_RERANK:
        return {"reponse": "Aucun passage pertinent n'a ete trouve pour cette question.",
                "citations": [], "verifie": False}

    contexte = "\n\n".join(f"[{i + 1}] {p['text']}" for i, p in enumerate(passages))
    prompt = (
        "Tu es un assistant qui repond UNIQUEMENT a partir des extraits fournis, en francais. "
        "Cite le numero de chaque extrait utilise entre crochets, par exemple [1]. "
        "Si les extraits ne permettent pas de repondre, dis-le clairement et ne rien inventer.\n\n"
        f"Extraits :\n{contexte}\n\nQuestion : {query}\nReponse :"
    )
    reponse = _appeler_ollama(prompt)

    notes = [couverture(reponse, p["text"]) for p in passages]
    cites = [p for p, s in sorted(zip(passages, notes), key=lambda ps: -ps[1]) if s >= SEUIL_COUVERTURE]
    verifie = bool(cites) and passages[0]["score"] >= PLANCHER_RERANK
    citations = cites or passages[:1]
    return {
        "reponse": reponse,
        "citations": [{"chunk_id": p["chunk_id"], "document_id": p["document_id"],
                       "source": p["source"]} for p in citations],
        "verifie": verifie,
    }


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "De quoi parle ce corpus ?"
    print(json.dumps(answer(q), ensure_ascii=False, indent=2))
