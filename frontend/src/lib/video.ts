// Client API of the video module ("capsule vidéo"): sources and extractive question answering.
import { request } from "./api";

export type SourceStatus = "pending" | "transcribing" | "indexing" | "ready" | "error";

export type Source = {
  id: string;
  project_id: string | null;
  source_type: "video";
  title: string;
  url: string;
  language: string | null;
  duration: number | null; // seconds
  status: SourceStatus;
  error: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

export type AskStatus = "repondu" | "confiance_faible" | "hors_sujet";

export type AskResponse = {
  question: string;
  status: AskStatus;
  answer: string;
  citation: { text: string; timestamp: string; passage: number } | null;
  rephrasing: string | null;
  passages: { chunk_id: string; timestamp: string; start: number; end: number; text: string; rerank: number }[];
  timings: Record<string, number>;
};

export type VideoUpload = { file: File; title?: string; language?: string; projectId?: string };

export const VIDEO_EXTENSIONS = [".mp4", ".webm", ".mkv", ".mov", ".m4v"];

export const videoApi = {
  listSources: () => request<Source[]>("/sources"),
  getSource: (id: string) => request<Source>(`/sources/${id}`),
  deleteSource: (id: string) => request<void>(`/sources/${id}`, { method: "DELETE" }),
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
  ask: (sourceId: string, question: string) =>
    request<AskResponse>("/ask", { method: "POST", body: JSON.stringify({ source_id: sourceId, question }) }),
};
