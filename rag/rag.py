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


def _appeler_ollama(prompt, num_predict=200, timeout=900, modele=MODELE_LLM):
    # num_predict borne la longueur de la reponse : generation tres lente en CPU sur cette
    # machine (environ 9 s/jeton observes avec qwen2.5:3b), d'ou le timeout genereux.
    corps = json.dumps({"model": modele, "prompt": prompt, "stream": False,
                        "options": {"temperature": 0, "seed": 42, "num_predict": num_predict}}
                       ).encode("utf-8")
    requete = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=corps,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        return json.loads(reponse.read())["response"].strip()


# Versions du prompt de generation, comparees par comparer_prompts.py sur le lot de validation.
# v1 : prompt d'origine. v2 : regles explicites. v3 : v2 + exemple de reponse + titre de l'article.
PROMPT_PAR_DEFAUT = "v4"   # choisi sur la validation, confirme sur le test (results/comparaison_prompts_test.csv)
PHRASE_REFUS = "Les extraits fournis ne permettent pas de répondre à cette question."
_REGLES = (
    "Tu es l'assistant de recherche de ResearchMind. Tu réponds à une question en t'appuyant UNIQUEMENT "
    "sur les extraits d'articles scientifiques ci-dessous (ils sont en anglais).\n\n"
    "Règles :\n"
    "1. Réponds en français, en 2 à 4 phrases courtes et précises.\n"
    "2. Après chaque information, écris entre crochets le numéro de l'extrait d'où elle vient, par exemple [2].\n"
    "3. Garde tels quels les noms de méthodes et de modèles, les sigles et les chiffres.\n"
    "4. N'ajoute aucune information absente des extraits.\n"
    f"5. Si aucun extrait ne permet de répondre, écris seulement : « {PHRASE_REFUS} »\n\n"
)
# Exemple invente (aucun lien avec le corpus ni avec le jeu de test) : montre le format attendu.
_EXEMPLE = (
    "Exemple de réponse attendue, sur un autre sujet :\n"
    "Question : Quelle précision le modèle NeuroTag obtient-il sur le jeu CellBench ?\n"
    "Réponse : NeuroTag atteint une précision de 91,2 % sur CellBench [2]. Les auteurs attribuent ce résultat "
    "à leur module d'attention croisée [2], absent des modèles de référence [4].\n\n"
)
_titres = None


def _titre(document_id):
    """Titre d'un article du corpus (vide pour une video ou si l'index est absent)."""
    global _titres
    if _titres is None:
        chemin = Path(__file__).resolve().parents[1] / "data_latex" / "data" / "index" / "documents.jsonl"
        _titres = {}
        if chemin.exists():
            for ligne in chemin.read_text(encoding="utf-8").splitlines():
                d = json.loads(ligne)
                _titres[d["doc_id"]] = d.get("title", "")
    return _titres.get(document_id, "")


def construire_prompt(query, passages, version=PROMPT_PAR_DEFAUT):
    if version == "v1":
        contexte = "\n\n".join(f"[{i + 1}] {p['text']}" for i, p in enumerate(passages))
        return (
            "Tu es un assistant qui repond UNIQUEMENT a partir des extraits fournis, en francais. "
            "Cite le numero de chaque extrait utilise entre crochets, par exemple [1]. "
            "Si les extraits ne permettent pas de repondre, dis-le clairement et ne rien inventer.\n\n"
            f"Extraits :\n{contexte}\n\nQuestion : {query}\nReponse :"
        )
    if version == "v2":
        contexte = "\n\n".join(f"[{i + 1}] {p['text']}" for i, p in enumerate(passages))
        return f"{_REGLES}Extraits :\n{contexte}\n\nQuestion : {query}\nRéponse :"
    if version == "v3":
        def entete(p):
            t = _titre(p.get("document_id", ""))
            return f"(Article : {t}) " if t else ""
        contexte = "\n\n".join(f"[{i + 1}] {entete(p)}{p['text']}" for i, p in enumerate(passages))
        return f"{_REGLES}{_EXEMPLE}Extraits :\n{contexte}\n\nQuestion : {query}\nRéponse :"
    if version == "v4":   # v3 + moins de refus a tort, reponses completes (defauts observes en validation)
        regles = _REGLES.replace(
            f"5. Si aucun extrait ne permet de répondre, écris seulement : « {PHRASE_REFUS} »\n\n",
            "5. Si la question demande plusieurs éléments (chiffres, conditions, hypothèses), donne-les tous.\n"
            "6. Si un extrait contient au moins une partie de la réponse, donne cette partie. N'écris "
            f"« {PHRASE_REFUS} » que si aucun extrait ne parle du sujet de la question.\n\n")
        def entete(p):
            t = _titre(p.get("document_id", ""))
            return f"(Article : {t}) " if t else ""
        contexte = "\n\n".join(f"[{i + 1}] {entete(p)}{p['text']}" for i, p in enumerate(passages))
        return f"{regles}{_EXEMPLE}Extraits :\n{contexte}\n\nQuestion : {query}\nRéponse :"
    raise ValueError(f"Version de prompt inconnue : {version}")


def answer(query, top_k=5):
    """Reponse de qwen2.5:3b a partir des passages de search(), avec citations. Voir contrat_api.md."""
    passages = search(query, top_k)
    if not passages or passages[0]["score"] < PLANCHER_RERANK:
        return {"reponse": "Aucun passage pertinent n'a ete trouve pour cette question.",
                "citations": [], "verifie": False}

    reponse = _appeler_ollama(construire_prompt(query, passages))

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
