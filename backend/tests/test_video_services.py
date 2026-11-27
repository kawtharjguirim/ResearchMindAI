"""Tests des fonctions pures du module vidéo : aucun modèle, aucun appel à Ollama."""
from app.services.video.chunking import construire_chunks, decouper, document_id
from app.services.video.qa import (controler_preuve, controler_reformulation, decider, horodater,
                                   trouver_citation)
from app.services.video.text import couverture, hms, normaliser, phrases


def seg(start, end, text):
    return {"start": start, "end": end, "text": text}


def passage(text, start=0.0, end=30.0):
    return {"chunk": {"text": text, "start": start, "end": end,
                      "timestamp": f"{hms(start)} - {hms(end)}"}}


# ---------- text ----------

def test_normaliser_retire_accents_et_mots_vides():
    assert normaliser("Le modèle a entraîné des données") == ["modele", "entraine", "donnees"]
    # Comportement hérité du prototype (conservé pour garder les mêmes résultats) :
    # les mots vides accentués sont comparés après suppression des accents, donc « été » reste.
    assert normaliser("été") == ["ete"]


def test_phrases_et_hms():
    assert phrases("Bonjour. Ça va ? Oui !") == ["Bonjour.", "Ça va ?", "Oui !"]
    assert hms(3725.9) == "01:02:05"


def test_couverture():
    assert couverture("le GPS utilise la relativité", "La relativité est utilisée par le GPS") == 2 / 3
    assert couverture("", "texte") == 0.0


# ---------- chunking ----------

def test_decouper_respecte_duree_et_chevauchement():
    segments = [seg(i * 10, i * 10 + 10, f"phrase {i}") for i in range(10)]
    groupes = decouper(segments, max_secondes=45, max_mots=200, chevauchement=1)
    assert all(g[-1]["end"] - g[0]["start"] <= 45 for g in groupes)
    for a, b in zip(groupes, groupes[1:]):
        assert b[0] is a[-1]          # un segment repris au début du chunk suivant


def test_construire_chunks_provenance():
    segments = [seg(0, 5, "Premier."), seg(5, 12.4, "Second.")]
    chunks = construire_chunks(segments, source="video.mp4", titre="Test", langue="fr")
    assert len(chunks) == 1
    c = chunks[0]
    assert c["chunk_id"] == f"{document_id('video.mp4')}_0000"
    assert c["timestamp"] == "00:00:00 - 00:00:12"
    assert c["text"] == "Premier. Second."
    assert c["source_type"] == "video" and c["language"] == "fr"


# ---------- règle de décision combinée (plancher 0,02, seuil 0,07) ----------

def test_decider_plancher_l_emporte_sur_le_llm():
    assert decider({"repond": True}, 0.0147) == "hors_sujet"


def test_decider_llm_oui_au_dessus_du_plancher():
    assert decider({"repond": True}, 0.0251) == "repondu"


def test_decider_llm_non():
    assert decider({"repond": False}, 0.094) == "confiance_faible"
    assert decider({"repond": False}, 0.049) == "hors_sujet"


# ---------- contrôles extractifs ----------

TEXTE = ("Le GPS doit corriger l'effet de la relativité. Sans cette correction, "
         "la position dériverait de dix kilomètres par jour. C'est énorme.")


def test_controler_preuve_refuse_une_phrase_inventee():
    passages = [passage(TEXTE)]
    r = controler_preuve({"phrase": "Les satellites utilisent des horloges atomiques", "extrait": 1,
                          "repond": True}, passages)
    assert r["repond_llm"] is True and r["repond"] is False


def test_trouver_citation_renvoie_la_phrase_exacte():
    passages = [passage("Rien à voir ici."), passage(TEXTE)]
    c = trouver_citation("sans cette correction la position deriverait de 10 km par jour", passages, 2)
    assert c["texte"] == "Sans cette correction, la position dériverait de dix kilomètres par jour."
    assert c["passage"] == 2 and not c["hors_extrait_designe"]


def test_trouver_citation_rien_de_proche():
    assert trouver_citation("les pingouins vivent en Antarctique", [passage(TEXTE)], 1) is None


def test_horodater_retrouve_le_segment():
    segments = [seg(0, 4, "Le GPS doit corriger l'effet de la relativité."),
                seg(4, 9, "Sans cette correction, la position dériverait"),
                seg(9, 12, "de dix kilomètres par jour.")]
    chunk = passage(TEXTE, 0, 12)["chunk"]
    assert horodater("Sans cette correction, la position dériverait de dix kilomètres", chunk,
                     segments) == "00:00:04"
    assert horodater("phrase absente", chunk, segments) == "00:00:00"


def test_controler_reformulation():
    citation = "Sans cette correction, la position dériverait de dix kilomètres par jour."
    ok = controler_reformulation("La position dériverait de dix kilomètres chaque jour sans correction.",
                                 citation, "Que se passe-t-il sans correction ?")
    assert ok["negation_suspecte"] is False
    invente = controler_reformulation("Les satellites dériveraient à cause des horloges atomiques.",
                                      citation, "Que se passe-t-il ?")
    assert invente["retenue"] is False and "satellites" in invente["mots_ajoutes"]
    negation = controler_reformulation("La position ne dériverait pas.", "La position dériverait.", "?")
    assert negation["negation_suspecte"] is True and negation["retenue"] is False
