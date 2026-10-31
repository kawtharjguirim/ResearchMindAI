"""
Module « capsule vidéo » : transcription, découpage, recherche hybride et
questions-réponses extractives sur une vidéo.

Pipeline :
  transcription.transcrire()     vidéo  -> segments horodatés (faster-whisper)
  chunking.construire_chunks()   segments -> chunks avec provenance
  search.Index                   BM25 + E5 -> RRF -> cross-encodeur
  qa.VideoQA.repondre()          question -> citation exacte + horodatage (qwen2.5:3b)

Les dépendances lourdes (faster-whisper, sentence-transformers, rank-bm25, numpy)
sont importées à l'usage : les fonctions pures restent testables sans elles.
"""
