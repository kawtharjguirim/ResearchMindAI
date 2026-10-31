import { getSupabase } from "./supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ProjectStatus = "in_progress" | "literature_review" | "writing";

export type Project = {
  id: string;
  title: string;
  problem: string;
  research_question: string;
  objectives: string[];
  hypotheses: string[];
  status: ProjectStatus;
  progress: number;
  sources: { pdf: number; web: number; video: number; figure: number; personal: number };
  created_at: string;
  updated_at: string;
};

export type ProjectInput = {
  title: string;
  problem?: string;
  research_question?: string;
  objectives?: string[];
  hypotheses?: string[];
};

export type DashboardStats = {
  active_projects: number;
  indexed_sources: number;
  questions_asked: number;
  pending_suggestions: number;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const {
    data: { session },
  } = await getSupabase().auth.getSession();
  if (!session) throw new ApiError(401, "You are signed out. Please sign in again.");

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is the backend running?`);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  me: () => request<{ id: string; email: string | null; full_name: string | null }>("/me"),
  listProjects: () => request<Project[]>("/projects"),
  stats: () => request<DashboardStats>("/projects/stats"),
  createProject: (body: ProjectInput) => request<Project>("/projects", { method: "POST", body: JSON.stringify(body) }),
  updateProject: (id: string, body: Partial<ProjectInput> & { status?: ProjectStatus; progress?: number }) =>
    request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: "DELETE" }),
};
