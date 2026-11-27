"""
Questions-réponses extractives sur une vidéo (repris de rag.py, mode extractif uniquement).

  1. Recherche    : Index.rechercher -> TOP_K passages ; rerank max < plancher -> hors sujet sans LLM
  2. Vérification : le LLM nomme l'information demandée et recopie la phrase qui la donne ;
                    la phrase doit se retrouver dans l'extrait (contrôle sans LLM)
  3. Décision     : règle combinée (plancher 0,02, seuil 0,07)
  4. Réponse      : phrase EXACTE de la transcription, calculée par le code, avec son horodatage ;
                    le LLM ajoute une reformulation de 1 à 2 phrases, écartée si elle ajoute des
                    mots absents de la citation ou change une négation.
"""
import re
import time

from . import llm
from .config import (LANGUES, MOTS_LIBRES, MSG_HORS_SUJET, MSG_SANS_CITATION, PLANCHER_RERANK,
                     SEUIL_INCLUSE, SEUIL_PREUVE, SEUIL_RERANK, TOP_K)
from .text import couverture, hms, normaliser, phrases

# ---------- Prompts ----------

SCHEMA_VERIFICATION = {
    "type": "object",
    "properties": {
        "information_demandee": {"type": "string"},
        "phrase": {"type": "string"},
        "extrait": {"type": "integer"},
        "repond": {"type": "boolean"},
    },
    "required": ["information_demandee", "phrase", "extrait", "repond"],
}

SYSTEME_VERIFICATION = ("Tu es un vérificateur strict. Tu juges si des extraits de la transcription "
                        "d'une vidéo contiennent la réponse à une question. Tu n'utilises que les "
                        "extraits, jamais tes propres connaissances.")

PROMPT_VERIFICATION = """Question : « {question} »

Extraits :
{extraits}

- "information_demandee" : en quelques mots, l'information précise que la question demande
Cherche ensuite dans les extraits la phrase qui donne cette information.
- "phrase" : cette phrase, recopiée MOT POUR MOT depuis un extrait ("" si aucune phrase ne répond)
- "extrait" : le numéro de l'extrait qui la contient (0 si aucun)
- "repond" : true si cette phrase donne l'information demandée par la question, même partiellement ;
  false si les extraits parlent seulement du même thème sans donner cette information,
  ou si la question porte sur quelque chose que les extraits ne mentionnent pas."""

SCHEMA_REFORMULATION = {
    "type": "object",
    "properties": {"reformulation": {"type": "string"}},
    "required": ["reformulation"],
}

SYSTEME_REFORMULATION = ("Tu redis en français, en 1 ou 2 phrases courtes, une citation tirée de la "
                         "transcription d'une vidéo. Tu n'utilises QUE ce que dit la citation : aucun "
                         "fait, chiffre, nom, cause, exemple ou conséquence qui n'y figure pas, aucune "
                         "connaissance personnelle, aucune déduction. Tu ne commences pas par oui ou "
                         "par non. Tu ne changes pas le sens : pas de négation si la citation n'en a "
                         "pas, et tu gardes celles qu'elle contient.")

PROMPT_REFORMULATION = """Question : « {question} »
Citation : « {citation} »

- "reformulation" : la citation redite simplement en 1 ou 2 phrases, au plus près de ses mots, sans
  rien ajouter. Si elle ne répond qu'en partie à la question, dis seulement ce qu'elle dit."""


# ---------- Fonctions pures (testées sans LLM) ----------

def decider(v: dict, rerank_max: float, seuil: float = SEUIL_RERANK,
            plancher: float = PLANCHER_RERANK) -> str:
    """
    Verdict final : 'repondu', 'confiance_faible' ou 'hors_sujet'.
      rerank max < plancher          -> hors_sujet, quel que soit l'avis du LLM
      LLM oui                        -> repondu
      LLM non et rerank max >= seuil -> confiance_faible ; sinon hors_sujet
    """
    if rerank_max < plancher:
        return "hors_sujet"
    if v["repond"]:
        return "repondu"
    return "confiance_faible" if rerank_max >= seuil else "hors_sujet"


def formater_extraits(passages: list[dict]) -> str:
    return "\n\n".join(f"[{n}] {p['chunk']['text']}" for n, p in enumerate(passages, start=1))


def controler_preuve(r: dict, passages: list[dict]) -> dict:
    """Un « oui » n'est retenu que si la phrase citée existe vraiment dans l'extrait."""
    n = r.get("extrait", 0)
    r["preuve"] = couverture(r["phrase"], passages[n - 1]["chunk"]["text"]) \
        if 1 <= n <= len(passages) else 0.0
    r["repond_llm"] = r["repond"]
    r["repond"] = bool(r["repond"]) and r["preuve"] >= SEUIL_PREUVE
    return r


def trouver_citation(phrase_llm: str, passages: list[dict], n: int, scorer=None) -> dict | None:
    """
    Phrase EXACTE de la transcription la plus proche de celle recopiée par le LLM.
    Candidats : chaque phrase de l'extrait désigné (n), et chaque paire de phrases consécutives ;
    score F1 entre les mots des deux textes. Si l'extrait désigné ne contient rien d'assez proche,
    on cherche dans les autres passages lus.
    Copie longue (plus de deux phrases recopiées) : parmi les phrases de l'extrait désigné
    entièrement incluses dans la copie, celle que scorer(textes) juge la plus pertinente.
    Renvoie None si rien ne correspond.
    """
    phrase_llm = re.sub(r"^\s*(\[\d+\]\s*)+", "", phrase_llm or "")   # « [1] » recopié du prompt
    if not normaliser(phrase_llm):
        return None
    designe = [n - 1] if 1 <= n <= len(passages) else []
    meilleur = None
    for groupe in (designe, [i for i in range(len(passages)) if i not in designe]):
        for i in groupe:
            ph = phrases(passages[i]["chunk"]["text"])
            for cand in ph + [a + " " + b for a, b in zip(ph, ph[1:])]:
                rappel, precision = couverture(phrase_llm, cand), couverture(cand, phrase_llm)
                f1 = 2 * rappel * precision / (rappel + precision) if rappel + precision else 0.0
                if meilleur is None or f1 > meilleur["f1"]:
                    meilleur = {"texte": cand, "passage": i + 1, "couverture": rappel, "f1": f1,
                                "hors_extrait_designe": i + 1 != n}
        if meilleur and meilleur["couverture"] >= SEUIL_PREUVE:
            break
    if meilleur:
        meilleur["methode"] = "phrase_du_llm"
    if (not meilleur or meilleur["couverture"] < SEUIL_PREUVE) and designe and scorer:
        incluses = [p for p in phrases(passages[designe[0]]["chunk"]["text"])
                    if normaliser(p) and couverture(p, phrase_llm) >= SEUIL_INCLUSE]
        if len(incluses) > 2:
            scores = list(scorer(incluses))
            k = max(range(len(incluses)), key=lambda j: scores[j])
            return {"texte": incluses[k], "passage": n, "hors_extrait_designe": False,
                    "couverture": round(couverture(phrase_llm, incluses[k]), 2),
                    "f1": 0.0, "methode": f"copie_longue_{len(incluses)}_phrases_reranker",
                    "score_reranker": round(float(scores[k]), 3)}
    if not meilleur or meilleur["couverture"] < SEUIL_PREUVE:
        return None
    meilleur["couverture"], meilleur["f1"] = round(meilleur["couverture"], 2), round(meilleur["f1"], 2)
    return meilleur


def horodater(citation: str, chunk: dict, segments: list[dict] | None) -> str:
    """Début du segment de transcription où commence la citation (sinon début du chunk)."""
    if segments:
        tete = normaliser(citation)[:6]
        mots = [(m, seg["start"]) for seg in segments
                if seg["end"] > chunk["start"] - 1 and seg["start"] < chunk["end"] + 1
                for m in normaliser(seg["text"])]
        for k in range(len(mots) - len(tete) + 1):
            if tete and [m for m, _ in mots[k:k + len(tete)]] == tete:
                return hms(mots[k][1])
    return chunk["timestamp"].split(" - ")[0]


def _negation(texte: str) -> bool:
    return bool(re.search(r"\bn(?:e\b|['’])|\b(?:non|jamais|aucune?|rien|not|never)\b", texte.lower()))


def _proche(mot: str, vus: set[str]) -> bool:
    """Même mot, ou même racine grossière (5 premières lettres) : « rapide » ~ « rapidement »."""
    return mot in vus or (len(mot) >= 5 and any(len(v) >= 5 and v[:5] == mot[:5] for v in vus))


def controler_reformulation(reformulation: str, citation: str, question: str) -> dict:
    """
    Contrôle sans LLM d'une reformulation : mots absents de la citation (hors MOTS_LIBRES),
    séparés entre ceux repris de la question et les autres, et négation ajoutée ou perdue.
    Retenue seulement sans mot ajouté hors question et sans négation suspecte.
    """
    vus_c, vus_q = set(normaliser(citation)), set(normaliser(question))
    hors = [m for m in dict.fromkeys(normaliser(reformulation))
            if m not in MOTS_LIBRES and not _proche(m, vus_c)]
    de_q = [m for m in hors if _proche(m, vus_q)]
    ajoutes = [m for m in hors if m not in de_q]
    neg = _negation(reformulation) != _negation(citation)
    return {"mots_ajoutes": ajoutes, "mots_de_la_question": de_q, "negation_suspecte": neg,
            "retenue": bool(reformulation.strip()) and not ajoutes and not neg}


# ---------- Pipeline ----------

class VideoQA:
    """Questions-réponses extractives sur l'index d'une vidéo."""

    def __init__(self, index, segments: list[dict] | None = None, langue_video: str | None = None,
                 seuil_rerank: float = SEUIL_RERANK, plancher_rerank: float = PLANCHER_RERANK,
                 ecarter=None, toujours=None):
        self.index = index
        self.segments = segments
        self.seuil_rerank = seuil_rerank
        self.plancher_rerank = plancher_rerank
        code = langue_video or index.chunks[0].get("language") or "fr"
        self.langue = LANGUES.get(code, code)
        self.appels: list[dict] = []
        # Passages à ne jamais retenir pour répondre (ex. bibliographie d'un article)
        self.ecarter = ecarter
        # Passages à garder dans la réponse même s'ils ne sont pas dans les candidats (ex. résumé d'un article)
        self.toujours = toujours or []

    def verifier(self, question: str, passages: list[dict]) -> dict:
        r = llm.chat([{"role": "system", "content": SYSTEME_VERIFICATION},
                      {"role": "user", "content": PROMPT_VERIFICATION.format(
                          question=question, extraits=formater_extraits(passages))}],
                     SCHEMA_VERIFICATION, appels=self.appels, etape="verification")
        return controler_preuve(r, passages)

    def reformuler(self, question: str, citation: str) -> str:
        r = llm.chat([{"role": "system", "content": SYSTEME_REFORMULATION},
                      {"role": "user", "content": PROMPT_REFORMULATION.format(
                          question=question, citation=citation)}],
                     SCHEMA_REFORMULATION, appels=self.appels, etape="reformulation")
        return " ".join(phrases(r.get("reformulation", ""))[:2])

    def extraire(self, question: str, v: dict, passages: list[dict]) -> dict:
        """Citation calculée par le code, horodatage, reformulation contrôlée."""
        scorer = lambda textes: self.index.scorer(question, textes)  # noqa: E731
        c = trouver_citation(v.get("phrase", ""), passages, v.get("extrait", 0), scorer)
        if c is None:
            return {"citation": None, "reformulation": None, "reponse": MSG_SANS_CITATION,
                    "passages_cites": []}
        p = passages[c["passage"] - 1]
        c["timestamp"] = horodater(c["texte"], p["chunk"], self.segments)
        brute = self.reformuler(question, c["texte"])
        ctrl = controler_reformulation(brute, c["texte"], question)
        r1, r2 = couverture(brute, c["texte"]), couverture(c["texte"], brute)
        ctrl["identique_a_la_citation"] = r1 + r2 > 0 and 2 * r1 * r2 / (r1 + r2) >= 0.9
        reponse = f"« {c['texte']} » [{c['timestamp']}]"
        if ctrl["retenue"] and not ctrl["identique_a_la_citation"]:
            reponse += "\n\n" + brute
        return {"citation": c, "reformulation": {"texte": brute, **ctrl}, "reponse": reponse,
                "passages_cites": [p]}

    def repondre(self, question: str) -> dict:
        """
        Renvoie : question, statut ("repondu" | "confiance_faible" | "hors_sujet"), reponse,
        citation, reformulation, passages (TOP_K), passages_cites, resultats (candidats et scores),
        verification, temps (secondes par étape), appels (durées Ollama).
        """
        temps: dict[str, float] = {}
        self.appels = []
        out = {"question": question, "verification": None, "citation": None,
               "reformulation": None, "passages_cites": [], "appels": self.appels}

        t0 = time.perf_counter()
        out["resultats"] = self.index.rechercher(question)
        if self.ecarter:
            out["resultats"] = [r for r in out["resultats"] if not self.ecarter(r["chunk"]["text"])]
        temps["recherche"] = time.perf_counter() - t0
        passages = out["resultats"][:TOP_K]
        for t in self.toujours:
            if not any(p["chunk"]["chunk_id"] == t["chunk_id"] for p in passages):
                score = float(self.index.scorer(question, [t["text"]])[0])
                passages = [{"chunk": t, "rerank": score}] + passages[: TOP_K - 1]
        out["passages"] = passages
        rerank_max = max(p["rerank"] for p in passages) if passages else 0.0

        # Sous le plancher, le verdict ne dépend pas du LLM : inutile de l'appeler
        if rerank_max < self.plancher_rerank:
            out.update(statut="hors_sujet", reponse=MSG_HORS_SUJET, temps=temps, sous_plancher=True)
            return out

        t0 = time.perf_counter()
        v = out["verification"] = self.verifier(question, passages)
        temps["verification"] = time.perf_counter() - t0
        statut = decider(v, rerank_max, self.seuil_rerank, self.plancher_rerank)
        if statut == "hors_sujet":
            out.update(statut=statut, reponse=MSG_HORS_SUJET, temps=temps)
            return out

        t0 = time.perf_counter()
        e = self.extraire(question, v, passages)
        temps["reformulation"] = time.perf_counter() - t0
        if e["citation"] is None:
            statut = "confiance_faible"
        out.update(e, statut=statut, temps=temps)
        return out
