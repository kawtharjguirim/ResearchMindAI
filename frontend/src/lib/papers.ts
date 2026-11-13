// arXiv papers of the corpus (data_latex): library, metadata, cited passage and compiled PDF.
import type { Tone } from "@/components/ui";
import { request, requestBlob } from "./api";

export type PaperPassage = { chunk_id: string; section: string; text: string };

export type PaperSummary = {
  doc_id: string;
  title: string;
  domain: string;
  categories: string;
  authors: string;
  update_date: string;
  license: string;
  arxiv_url: string;
  abstract: string;
  has_pdf: boolean;
};

export type Paper = PaperSummary & { passage: PaperPassage | null };

// Corpus domain keys (data_latex folder names) -> display label and badge tone.
export const DOMAINS: Record<string, [string, Tone]> = {
  maths: ["Mathematics", "violet"],
  informatique: ["Computer science", "blue"],
  physique: ["Physics", "orange"],
  biologie: ["Biology", "green"],
  "finance-eco": ["Finance & economics", "red"],
  statistiques: ["Statistics", "gray"],
};

export const domainLabel = (key: string) => DOMAINS[key]?.[0] ?? key;
export const domainTone = (key: string): Tone => DOMAINS[key]?.[1] ?? "gray";

// "http://creativecommons.org/licenses/by/4.0/" -> "CC BY 4.0"
export function licenseLabel(url: string) {
  if (url.includes("publicdomain/zero")) return "CC0";
  const m = /licenses\/([a-z-]+)\/([\d.]+)/.exec(url);
  return m ? `CC ${m[1].toUpperCase()} ${m[2]}` : url;
}

export const papersApi = {
  list: () => request<PaperSummary[]>("/papers"),
  get: (docId: string, chunkId?: string | null) => {
    const query = chunkId ? `?chunk=${encodeURIComponent(chunkId)}` : "";
    return request<Paper>(`/papers/${encodeURIComponent(docId)}${query}`);
  },
  pdf: (docId: string) => requestBlob(`/papers/${encodeURIComponent(docId)}/pdf`),
};
