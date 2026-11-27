// Human review of the evaluation set (rag/eval/jeu_corpus.json).
import type { Tone } from "@/components/ui";
import { request } from "./api";

export type EvalStatus = "a_valider" | "valide" | "corrige" | "rejete";

export type EvalQuestion = {
  id: string;
  domaine: string;
  split: "validation" | "test";
  document_id: string;
  chunk_id: string;
  titre: string;
  section: string;
  passage: string;
  question: string;
  reference: string;
  question_initiale: string;
  reference_initiale: string;
  auteur: string;
  statut: EvalStatus;
  commentaire: string;
};

export type EvalUpdate = Partial<Pick<EvalQuestion, "statut" | "question" | "reference" | "commentaire">>;

export const EVAL_STATUS: Record<EvalStatus, [string, Tone]> = {
  a_valider: ["To review", "gray"],
  valide: ["Validated", "green"],
  corrige: ["Corrected", "blue"],
  rejete: ["Rejected", "red"],
};

export const evaluationApi = {
  list: () => request<EvalQuestion[]>("/evaluation/questions"),
  update: (id: string, body: EvalUpdate) =>
    request<EvalQuestion>(`/evaluation/questions/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(body) }),
};
