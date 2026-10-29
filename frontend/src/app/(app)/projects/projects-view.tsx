"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";
import { Badge, btnPrimary, btnSecondary, card, Progress, SourceIcon, type SourceType, type Tone } from "@/components/ui";
import { api, type DashboardStats, type Project, type ProjectInput, type ProjectStatus } from "@/lib/api";
import { NewProjectModal } from "./new-project-modal";

const STATUS: Record<ProjectStatus, [string, Tone]> = {
  in_progress: ["In progress", "violet"],
  literature_review: ["Literature review", "blue"],
  writing: ["Writing", "green"],
};

function updatedLabel(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "Updated just now";
  if (diff < 3600) return `Updated ${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `Updated ${Math.floor(diff / 3600)} h ago`;
  if (diff < 172800) return "Updated yesterday";
  return `Updated on ${new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}`;
}

function ProjectCard({ p }: { p: Project }) {
  const [label, tone] = STATUS[p.status];
  const sources = (Object.entries(p.sources) as [SourceType, number][]).filter(([, n]) => n > 0);
  return (
    <div className={`${card} flex flex-col p-6 transition hover:border-primary-200 dark:hover:border-primary-500/40`}>
      <div>
        <Badge tone={tone}>{label}</Badge>
      </div>
      <h3 className="mt-4 text-base font-semibold leading-snug text-gray-800 dark:text-white/90">
        <Link href={`/research-twin?project=${p.id}`} className="hover:text-primary-600 dark:hover:text-primary-300">
          {p.title}
        </Link>
      </h3>
      <p className="mt-2 line-clamp-2 text-sm text-gray-500 dark:text-gray-400">
        {p.research_question || "Research question to be defined"}
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        {sources.length ? (
          sources.map(([type, n]) => (
            <span key={type} className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 dark:text-gray-300">
              <SourceIcon type={type} small />
              {n}
            </span>
          ))
        ) : (
          <span className="text-xs text-gray-400">No sources yet</span>
        )}
      </div>
      <div className="mt-auto pt-6">
        <div className="mb-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span className="inline-flex items-center gap-1">
            <Icon name="clock" className="size-3.5" />
            {updatedLabel(p.updated_at)}
          </span>
          <span>{p.progress}%</span>
        </div>
        <Progress value={p.progress} />
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className={`${card} min-h-[260px] animate-pulse p-6`}>
      <div className="h-5 w-24 rounded-full bg-gray-100 dark:bg-white/10" />
      <div className="mt-5 h-4 w-4/5 rounded-full bg-gray-100 dark:bg-white/10" />
      <div className="mt-3 h-3 w-full rounded-full bg-gray-100 dark:bg-white/10" />
      <div className="mt-2 h-3 w-2/3 rounded-full bg-gray-100 dark:bg-white/10" />
    </div>
  );
}

export function ProjectsView() {
  const toast = useToast();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [list, s] = await Promise.all([api.listProjects(), api.stats()]);
      setProjects(list);
      setStats(s);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function create(body: ProjectInput) {
    const created = await api.createProject(body);
    setProjects((list) => [created, ...(list ?? [])]);
    setStats((s) => (s ? { ...s, active_projects: s.active_projects + 1 } : s));
    setModal(false);
    toast("Project created");
  }

  const statCards: [string, number | undefined][] = [
    ["Active projects", stats?.active_projects],
    ["Indexed sources", stats?.indexed_sources],
    ["Questions asked", stats?.questions_asked],
    ["Suggestions to review", stats?.pending_suggestions],
  ];

  return (
    <>
      <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">My projects</h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Find your research projects and their sources</p>
          </div>
          <button type="button" onClick={() => setModal(true)} className={btnPrimary}>
            <Icon name="plus" className="size-4" />
            New project
          </button>
        </div>

        <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {statCards.map(([label, value], i) => (
            <div key={label} className={`${card} px-5 py-4`}>
              <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
              <p className={`mt-1 text-2xl font-semibold ${i === 3 ? "text-primary-600 dark:text-primary-300" : "text-gray-800 dark:text-white/90"}`}>
                {value ?? "–"}
              </p>
            </div>
          ))}
        </div>

        {error ? (
          <div className={`${card} mt-8 flex flex-col items-center px-6 py-12 text-center`}>
            <span className="inline-flex size-12 items-center justify-center rounded-full bg-error-50 text-error-500 dark:bg-error-500/15">
              <Icon name="alert" className="size-6" />
            </span>
            <p className="mt-4 font-semibold text-gray-800 dark:text-white/90">Your projects could not be loaded</p>
            <p className="mt-1 max-w-md text-sm text-gray-500 dark:text-gray-400">{error}</p>
            <button type="button" onClick={load} className={`${btnSecondary} mt-6`}>
              <Icon name="refresh" className="size-4" />
              Try again
            </button>
          </div>
        ) : (
          <div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {projects === null ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : (
              projects.map((p) => <ProjectCard key={p.id} p={p} />)
            )}
            <button
              type="button"
              onClick={() => setModal(true)}
              className="flex min-h-[260px] flex-col items-center justify-center gap-3 rounded-[20px] border-2 border-dashed border-primary-200 bg-primary-50/40 text-primary-600 transition hover:border-primary-400 hover:bg-primary-50 dark:border-primary-500/30 dark:bg-primary-500/5 dark:text-primary-300"
            >
              <span className="inline-flex size-12 items-center justify-center rounded-full bg-white shadow-theme-xs dark:bg-white/10">
                <Icon name="plus" className="size-6" />
              </span>
              <span className="text-sm font-medium">{projects?.length === 0 ? "Create your first project" : "Create a project"}</span>
            </button>
          </div>
        )}
      </div>
      {modal && <NewProjectModal onClose={() => setModal(false)} onCreate={create} />}
    </>
  );
}
