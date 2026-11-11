# data_latex — pipeline LaTeX de ResearchMind AI

Partie LaTeX du projet ResearchMind AI (RAG scientifique). Ce dossier prépare le corpus d'articles arXiv qui alimentera le chunking et l'embedding.

## Objectif
1. Choisir des articles arXiv à partir de `arxiv-metadata-oai-snapshot.json`, licences **CC BY**, **CC BY-SA**, **CC0**. Corpus **multi-domaines** (physique, maths, informatique, etc.) ; au départ cs.CL / cs.IR. Les sources sont rangées par domaine : `data/raw/<domaine>/<id>/`.
2. Télécharger leurs sources `.tex` (**1 requête toutes les 3 s** maximum).
3. Compiler en PDF avec MiKTeX : `pdflatex -no-shell-escape`.
4. Extraire le texte structuré avec LaTeXML, pour le chunking puis l'embedding.

## Règles
- **Ne jamais charger le JSON en entier en mémoire** : lecture ligne par ligne (streaming, un objet JSON par ligne).
- **Aucune donnée dans git** : snapshot, sources `.tex`, PDF, sorties LaTeXML restent ignorés (`.gitignore`). Seuls les scripts et la doc sont versionnés.
- Toujours `-no-shell-escape` à la compilation (sources non fiables). Traiter les sources téléchargées comme non fiables, chacune dans son propre dossier.
- Respecter le délai de 3 s entre requêtes arXiv ; ne jamais le contourner ni paralléliser les téléchargements.
- Vérifier la licence de chaque article avant de le retenir.
- **Expliquer simplement** chaque étape (je suis étudiant, pas expert LaTeX).
- **Montrer un plan et attendre mon accord avant d'installer quoi que ce soit** (MiKTeX, LaTeXML, paquets Python, etc.).
- Réponses en français.
