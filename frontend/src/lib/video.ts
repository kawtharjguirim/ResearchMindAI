// Client API of the video module ("capsule vidéo") and the generic RAG endpoints
// (/answer, /search) that work across video and simulated paper sources.
import { API_URL, request } from "./api";

export type SourceStatus = "pending" | "transcribing" | "indexing" | "ready" | "error";
export type AnySourceType = "pdf" | "web" | "figure" | "video" | "personal";

export type Source = {
  id: string;
  project_id: string | null;
  source_type: AnySourceType;
  title: string;
  url: string;
  language: string | null;
  duration: number | null; // seconds
  status: SourceStatus;
  error: string;
  chunk_count: number;
  excerpt: string | null;
  created_at: string;
  updated_at: string;
};

export type PlayLink = { url: string; expires_at: string };

export type AnswerStatus = "repondu" | "confiance_faible" | "hors_sujet";

export type AnswerCitation = {
  chunk_id: string;
  document_id: string;
  source: string;
  text: string;
  timestamp: string | null; // present for a video citation
  url: string | null; // present for a paper citation
};

export type Passage = { chunk_id: string; timestamp: string; start: number; end: number; text: string; rerank: number };

export type AnswerResponse = {
  reponse: string;
  citations: AnswerCitation[];
  verifie: boolean;
  question: string;
  status: AnswerStatus;
  passages: Passage[];
  timings: Record<string, number>;
};

export type SearchResult = { chunk_id: string; document_id: string; source: string; text: string; score: number; timestamp: string | null };

export type TranscriptChunk = { chunk_id: string; start: number; end: number; timestamp: string; text: string };

export type VideoUpload = { file: File; title?: string; language?: string; projectId?: string };

export type UrlImport = { url: string; title?: string; language?: string; projectId?: string };

// Identifiant YouTube d'une source importée par lien (le backend stocke l'URL canonique watch?v=...).
export const youtubeId = (url: string): string | null => /[?&]v=([A-Za-z0-9_-]{11})/.exec(url)?.[1] ?? null;

export const VIDEO_EXTENSIONS = [".mp4", ".webm", ".mkv", ".mov", ".m4v"];

// The <video> element loads the file directly (it cannot send an Authorization header), so the
// signed play-link's relative path needs the API origin prefixed.
export const playUrl = (link: PlayLink) => `${API_URL}${link.url}`;

export const videoApi = {
  listSources: () => request<Source[]>("/sources"),
  getSource: (id: string) => request<Source>(`/sources/${id}`),
  deleteSource: (id: string) => request<void>(`/sources/${id}`, { method: "DELETE" }),
  playLink: (id: string) => request<PlayLink>(`/sources/${id}/play-link`),
  getTranscript: (id: string) => request<TranscriptChunk[]>(`/sources/${id}/transcript`),
  // The video bytes are the request body (no multipart form): metadata goes in the query string.
  uploadVideo: ({ file, title, language, projectId }: VideoUpload) => {
    const params = new URLSearchParams({ filename: file.name });
    if (title?.trim()) params.set("title", title.trim());
    if (language) params.set("language", language);
    if (projectId) params.set("project_id", projectId);
    return request<Source>(`/sources/video?${params}`, {
      method: "POST",
      body: file,
      headers: { "Content-Type": file.type || "application/octet-stream" },
    });
  },
  importUrl: ({ url, title, language, projectId }: UrlImport) =>
    request<Source>("/sources/url", {
      method: "POST",
      body: JSON.stringify({ url, title: title?.trim() || null, language: language || null, project_id: projectId || null }),
    }),
  answer: (sourceId: string, question: string) =>
    request<AnswerResponse>("/answer", { method: "POST", body: JSON.stringify({ source_id: sourceId, question }) }),
  search: (query: string, sourceId?: string, topK = 5) =>
    request<SearchResult[]>("/search", {
      method: "POST",
      body: JSON.stringify({ query, source_id: sourceId, top_k: topK }),
    }),
};
