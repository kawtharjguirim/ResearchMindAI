# Validation Deep Learning — Transfer Learning et Fine-Tuning

Support de préparation pour la séance de validation (module Project Cognition & IA).
Les chiffres viennent des fichiers de résultats réels (dossier `results/colab_2026-11-15` du dépôt
d'expérimentation et `rag/results/`). Rien n'est estimé.

**Tâche étudiée** : retrouver, à partir d'une question scientifique, les passages qui y répondent
(*Scientific Passage Retrieval*, cahier des charges section 14).

---

## 1. Modèle pré-entraîné choisi et justification

**Choix : `intfloat/multilingual-e5-base` (mE5-base)**, utilisé en fusion avec BM25.

Un modèle pré-entraîné est un modèle déjà appris sur d'énormes quantités de texte par d'autres. Ici, mE5
transforme une phrase en une « empreinte de sens » (un vecteur de nombres) : deux phrases de même sens
ont des empreintes proches.

Six encodeurs ont été comparés sur les mêmes données (notebook 10, partie A) : MiniLM-L6, SciBERT,
SPECTER2, mE5-base, mE5-large, BGE-M3. Raisons du choix :

| Critère | Constat |
|---|---|
| Qualité | Meilleure moyenne en fusion avec BM25 parmi les modèles évalués sur les 3 benchmarks communs |
| **Multilingue** | Les utilisateurs posent leurs questions en français sur des articles en anglais : MiniLM et SciBERT sont anglais seulement |
| Taille et vitesse | mE5-large coûte environ 3,5 fois plus de temps par question pour un gain non décisif (SciFact : 0,7205 contre 0,7236) |
| Contrainte matérielle | Il doit tourner sur un GPU de 4 Go avec le reranker et le LLM |

SciBERT, pourtant spécialisé en science, s'effondre sans entraînement (nDCG@10 = 0,133 sur SciFact) : il n'a
jamais appris à comparer deux textes. C'est un résultat utile : « spécialisé » ne veut pas dire « adapté à la
recherche ».

## 2. Mise en œuvre du Transfer Learning

Le modèle est utilisé **sans réentraînement** :
- notebook 10 : évaluation de l'encodeur seul, puis fusion avec BM25 (RRF, k = 60) ;
- application : `rag/recherche.py`, configuré par `rag/config_recherche.json` ;
- preuve de fidélité : `rag/parite.py` rejoue SciFact avec le code de l'application et retrouve les chiffres du
  notebook (nDCG@10 hybride : 0,7247 contre 0,7236 ; cosinus des embeddings : 1,000).

## 3. Fine-Tuning et stratégie

Le fine-tuning prend le même modèle et le réentraîne un peu sur notre tâche.

| Élément | Choix |
|---|---|
| Données d'entraînement | SciFact train (647 questions) + NFCorpus train (2 072 questions) ; **jamais de questions de test** |
| Exemples | Triplets (question, passage pertinent, négatif difficile), jusqu'à 3 passages pertinents par question |
| Négatif difficile | Un passage classé 10e à 50e par le modèle d'origine mais non pertinent. Les places 1 à 9 sont évitées : elles contiennent souvent des passages pertinents non annotés |
| Perte | MultipleNegativesRanking (contrastive) : la question doit être plus proche de son passage que de tous les autres |
| Réglages | 1 époque, taux d'apprentissage 2e-5, lots de 32, précision mixte fp16, graine 42 |
| Matériel | Colab, GPU Tesla T4 ; entraînement d'environ 7 minutes |
| Résultat | Modèle sauvegardé (`models/mE5-base-finetuned`, 1,1 Go) |

Choix justifiés : une seule époque et un faible taux d'apprentissage pour limiter l'« oubli » des connaissances
du modèle d'origine ; deux domaines d'entraînement (SciFact et NFCorpus) pour éviter une spécialisation sur un
seul sujet.

## 4. Résultats et comparaison (nDCG@10, ensemble de test)

### Encodeur seul

| Benchmark | Pré-entraîné | Fine-tuné | Gain | Significatif (Wilcoxon) |
|---|---|---|---|---|
| NFCorpus (vu à l'entraînement) | 0,3279 | 0,3561 | **+0,0282** | oui (p = 0,0005) |
| SciFact (vu à l'entraînement) | 0,6961 | 0,6881 | −0,0080 | non (p = 0,66) |
| SciDocs (**jamais vu**) | 0,1783 | 0,1930 | **+0,0147** | oui (p = 0,00008) |
| **Moyenne** | **0,4008** | **0,4124** | **+0,0116** | |

### Fusion avec BM25 (système de l'application)

| Benchmark | Pré-entraîné | Fine-tuné | Gain | Significatif |
|---|---|---|---|---|
| NFCorpus | 0,3427 | 0,3601 | +0,0174 | oui (p = 0,003) |
| SciFact | 0,7238 | 0,7281 | +0,0043 | non (p = 0,53) |
| SciDocs | 0,1798 | 0,1831 | +0,0033 | non (p = 0,11) |
| **Moyenne** | **0,4154** | **0,4238** | **+0,0084** | |

Le Recall@100 (le bon passage est-il parmi les 100 premiers ?) augmente partout pour l'encodeur seul :
SciDocs 0,3995 → 0,4541, NFCorpus 0,2980 → 0,3458, SciFact 0,9360 → 0,9543.

### Sur notre corpus (questions en français sur les 139 articles arXiv)

*À compléter avec la section 6 (résultats mesurés sur `rag/eval/jeu_corpus.json`).*

## 5. Analyse critique

**Ce qui marche**
- Le fine-tuning améliore nettement le benchmark d'entraînement NFCorpus (+0,028) **et** le benchmark jamais vu
  SciDocs (+0,015) : le modèle a appris quelque chose de transférable, pas seulement à réciter ses exemples.
- Il améliore le rappel (candidats retrouvés) sur les trois benchmarks, utile pour un reranker en aval.

**Ce qui ne marche pas, ou pas encore**
- SciFact ne progresse pas (−0,008, non significatif) : 647 questions d'entraînement sont peu, et le modèle
  d'origine y était déjà bon.
- En fusion avec BM25, seul NFCorpus reste significatif : BM25 compense une partie de ce que le fine-tuning
  apporte.
- La sélection automatique du notebook (BM25 + mE5-base-FT) s'est faite sur 0,002 de différence en validation
  (0,5387 contre 0,5368) : c'est une égalité, pas une victoire.

**Limites et difficultés rencontrées**
- Matériel : GPU local de 4 Go, trop petit pour l'entraînement ; passage par Colab (T4, 16 Go).
- Données : le tableau de synthèse du notebook s'intitule « 5 benchmarks » mais n'en contient que 3
  (TREC-COVID et LitSearch non lancés, par durée).
- Langue : l'entraînement est en anglais seul. Un modèle fine-tuné sur une seule langue peut perdre en
  multilingue : vérifié sur nos questions en français (section 6).
- Données non adaptées à notre corpus : aucun jeu d'entraînement n'existait pour nos articles ; un jeu de test de
  118 questions a été créé (`rag/eval/jeu_corpus.json`), non utilisé pour entraîner.
- Environnement : version du notebook différente de la nôtre (erreurs de dossiers sur Drive, de configuration).

## 6. Résultats sur notre corpus

*(rempli après mesure)*

## 7. Autres expériences du pipeline

| Étape | Résultat |
|---|---|
| Baselines (notebook 07) | BM25 classique : nDCG@10 = 0,674 (SciFact) ; TF-IDF = 0,643 |
| Machine Learning (notebook 11, rerankers) | Régression logistique et SVM : gains significatifs sur 2 benchmarks sur 5, aucun ne passe le critère (3 sur 5). Random Forest : 1 sur 5 |
| LLM de réponse (qwen2.5:3b contre deepseek-r1:1.5b) | qwen2.5:3b gardé : ROUGE-L 0,191 contre 0,076 ; DeepSeek répond en anglais dans 20 cas sur 48 |
| Moteur vidéo | Aligné sur le moteur commun ; BM25 adapté au français (le réglage anglais dégradait les résultats) |

## 8. Démonstration prévue

1. Notebook 10 sur Colab : cellule d'évaluation du modèle d'origine, puis cellule de fine-tuning (le modèle
   sauvegardé permet de sauter l'entraînement de 7 min).
2. Test de parité : `python -I rag/parite.py`.
3. Application : une question en français, réponse avec citation, ouverture du PDF.
4. Comparaison avant/après sur nos questions : `python -I rag/evaluation_corpus.py --encodeur <modèle>`.
