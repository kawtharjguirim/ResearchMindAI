// Client API du graphe de connaissances : statistiques, extraction, propositions et vue du graphe.
import { request } from "./api";

export type EntityType = "Method" | "Dataset" | "Result" | "Concept";
export type Verification = "VERIFIED" | "NEEDS_REVIEW" | "REJECTED";
export type ProposalStatus = "pending" | "approved" | "rejected";
export type JobStatus = "queued" | "running" | "done" | "failed";

export type GraphStats = { noeuds: Record<string, number>; relations: Record<string, number> };

export type Proposal = {
  id: string;
  document_key: string; // corpus:<arXiv id> ou source:<uuid>
  document_title: string;
  entity_type: EntityType;
  name: string;
  excerpt: string; // phrase exacte du passage
  location: string; // « p. 3 », « § 2 »…
  verification_status: Verification;
  status: ProposalStatus;
  extraction_date: string;
  decided_at: string | null;
};

export type Job = {
  id: string;
  kind: "source" | "corpus";
  target: string;
  status: JobStatus;
  progress: number;
  total: number;
  message: string;
  created_at: string;
  updated_at: string;
};

export type GraphNode = { id: string; type: "Document" | EntityType; label: string; document_key?: string };
export type GraphEdge = { source: string; target: string; relation: string; phrase: string; location: string; document_key: string };
export type GraphView = { nodes: GraphNode[]; edges: GraphEdge[] };

export const ENTITY_TYPES: EntityType[] = ["Method", "Dataset", "Result", "Concept"];

// Lien vers le document d'origine d'une proposition ou d'une relation.
export function documentHref(documentKey: string): { href: string; external: boolean } | null {
  if (documentKey.startsWith("source:")) return { href: `/sources/${documentKey.slice(7)}`, external: false };
  if (documentKey.startsWith("corpus:")) return { href: `https://arxiv.org/abs/${documentKey.slice(7)}`, external: true };
  return null;
}

export const knowledgeApi = {
  stats: () => request<GraphStats>("/knowledge-graph"),
  view: (limit = 300) => request<GraphView>(`/knowledge-graph/view?limit=${limit}`),
  extractSource: (sourceId: string) => request<Job>(`/knowledge/extract/source/${sourceId}`, { method: "POST" }),
  extractCorpus: (limit: number) => request<Job>(`/knowledge/extract/corpus?limit=${limit}`, { method: "POST" }),
  job: (id: string) => request<Job>(`/knowledge/jobs/${id}`),
  proposals: (status: ProposalStatus = "pending") => request<Proposal[]>(`/knowledge/proposals?status=${status}`),
  approve: (id: string) => request<Proposal>(`/knowledge/proposals/${id}/approve`, { method: "POST" }),
  reject: (id: string) => request<Proposal>(`/knowledge/proposals/${id}/reject`, { method: "POST" }),
  history: () => request<Proposal[]>("/knowledge/history"),
};
