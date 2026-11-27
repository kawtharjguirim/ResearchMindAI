"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";
import { Badge, btnPrimary, btnSecondary, card, inputPill, Progress } from "@/components/ui";
import { api, type Project, type ProjectStatus, type ResearchTwin } from "@/lib/api";
import { videoApi, type Source } from "@/lib/video";

const STATUS: Record<ProjectStatus, [string, "violet" | "blue" | "green"]> = {
  in_progress: ["In progress", "violet"],
  literature_review: ["Literature review", "blue"],
  writing: ["Writing", "green"],
};

type SectionKey =
  | "problem"
  | "research_question"
  | "objectives"
  | "hypotheses"
  | "methods"
  | "results"
  | "limitations"
  | "research_gaps";

const SECTIONS: [SectionKey, string, string, "target" | "notes" | "book" | "bar" | "alert" | "search"][] = [
  ["problem", "Problem", "The scientific or practical problem addressed by this project.", "target"],
  ["research_question", "Research question", "The central question that guides the investigation.", "search"],
  ["objectives", "Objectives", "Concrete outcomes the project aims to achieve.", "target"],
  ["hypotheses", "Hypotheses", "Claims or assumptions that can be tested.", "book"],
  ["methods", "Methods", "Design, datasets, procedures and analytical approaches.", "notes"],
  ["results", "Results", "Observed findings and evidence collected so far.", "bar"],
  ["limitations", "Limitations", "Constraints, biases and threats to validity.", "alert"],
  ["research_gaps", "Research gaps", "Open questions and areas requiring further study.", "search"],
];

const toLines = (value: string) =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

const fromLines = (lines: string[] = []) => lines.join("\n");

export default function ResearchTwinPage() {
  const toast = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [project, setProject] = useState<Project | null>(null);
  const [twin, setTwin] = useState<ResearchTwin | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [draft, setDraft] = useState<Record<SectionKey, string>>({
    problem: "",
    research_question: "",
    objectives: "",
    hypotheses: "",
    methods: "",
    results: "",
    limitations: "",
    research_gaps: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadProject = useCallback(async (id: string) => {
    setLoading(true);
    setError("");
    try {
      const [p, t, s] = await Promise.all([
        api.getProject(id),
        api.getResearchTwin(id),
        videoApi.listSources(id),
      ]);
      setProject(p);
      setTwin(t);
      setSources(s);
      setDraft({
        problem: fromLines(t.problem),
        research_question: fromLines(t.research_question),
        objectives: fromLines(t.objectives),
        hypotheses: fromLines(t.hypotheses),
        methods: fromLines(t.methods),
        results: fromLines(t.results),
        limitations: fromLines(t.limitations),
        research_gaps: fromLines(t.research_gaps),
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api
      .listProjects()
      .then((items) => {
        setProjects(items);
        const queryId = new URLSearchParams(window.location.search).get("project");
        const selected = items.find((p) => p.id === queryId) ?? items[0];
        if (selected) {
          setProjectId(selected.id);
          loadProject(selected.id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError((err as Error).message);
        setLoading(false);
      });
  }, [loadProject]);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!projectId) return;
    setSaving(true);
    setError("");
    try {
      const body = Object.fromEntries(
        SECTIONS.map(([key]) => [key, toLines(draft[key])]),
      );
      const updated = await api.updateResearchTwin(projectId, body);
      setTwin(updated);
      toast("Research Twin saved");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function selectProject(id: string) {
    setProjectId(id);
    window.history.replaceState(null, "", `/research-twin?project=${encodeURIComponent(id)}`);
    loadProject(id);
  }

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Research Twin</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            A structured and evolving view of your research project
          </p>
        </div>
        {projects.length > 0 && (
          <select
            value={projectId}
            onChange={(e) => selectProject(e.target.value)}
            className={`${inputPill} max-w-[300px]`}
            aria-label="Select project"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.title}</option>
            ))}
          </select>
        )}
      </div>

      {error && (
        <div className={`${card} mt-6 px-5 py-4 text-sm text-error-500`}>{error}</div>
      )}

      {loading ? (
        <div className={`${card} mt-8 h-80 animate-pulse bg-gray-100 dark:bg-white/5`} />
      ) : !project ? (
        <div className={`${card} mt-8 flex flex-col items-center px-6 py-14 text-center`}>
          <span className="inline-flex size-12 items-center justify-center rounded-full bg-primary-50 text-primary-500 dark:bg-primary-500/15">
            <Icon name="layers" className="size-6" />
          </span>
          <p className="mt-4 font-semibold text-gray-800 dark:text-white/90">No project yet</p>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Create a project to initialize your Research Twin.
          </p>
          <Link href="/projects" className={`${btnSecondary} mt-6`}>Go to projects</Link>
        </div>
      ) : (
        <form onSubmit={save}>
          <div className={`${card} mt-8 p-6`}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <Badge tone={STATUS[project.status][1]}>{STATUS[project.status][0]}</Badge>
                <h2 className="mt-3 text-xl font-semibold text-gray-800 dark:text-white/90">{project.title}</h2>
              </div>
              <button type="submit" disabled={saving} className={btnPrimary}>
                <Icon name={saving ? "refresh" : "check"} className={`size-4 ${saving ? "animate-spin" : ""}`} />
                {saving ? "Saving…" : "Save Twin"}
              </button>
            </div>
            <div className="mt-5">
              <div className="mb-2 flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Project progress</span><span>{project.progress}%</span>
              </div>
              <Progress value={project.progress} />
            </div>
            <div className="mt-5 flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
              <span className="rounded-full bg-gray-100 px-3 py-1.5 dark:bg-white/10">
                {sources.length} linked {sources.length === 1 ? "source" : "sources"}
              </span>
              <span className="rounded-full bg-gray-100 px-3 py-1.5 dark:bg-white/10">
                {SECTIONS.reduce((count, [key]) => count + toLines(draft[key]).length, 0)} twin items
              </span>
              {twin && (
                <span className="rounded-full bg-gray-100 px-3 py-1.5 dark:bg-white/10">
                  Updated {new Date(twin.updated_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>

          <div className="mt-6 grid gap-5 lg:grid-cols-2">
            {SECTIONS.map(([key, label, description, icon]) => (
              <section key={key} className={`${card} p-6`}>
                <div className="flex items-start gap-3">
                  <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-600 dark:bg-primary-500/15 dark:text-primary-300">
                    <Icon name={icon} className="size-4" />
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">{label}</h3>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{description}</p>
                  </div>
                </div>
                <textarea
                  rows={5}
                  value={draft[key]}
                  onChange={(e) => setDraft((value) => ({ ...value, [key]: e.target.value }))}
                  placeholder="Enter one item per line"
                  className="mt-4 w-full resize-y rounded-2xl border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 placeholder:text-gray-400 focus:border-primary-300 focus:outline-0 focus:ring-3 focus:ring-primary-300/20 dark:border-gray-700 dark:text-white/90 dark:placeholder:text-white/30"
                />
              </section>
            ))}
          </div>

          <div className={`${card} mt-6 p-6`}>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">Linked sources</h3>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Evidence associated with this project</p>
              </div>
              <Link href="/sources" className={btnSecondary}>Manage sources</Link>
            </div>
            {sources.length === 0 ? (
              <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">No sources linked to this project yet.</p>
            ) : (
              <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                {sources.map((source) => (
                  <li key={source.id} className="rounded-2xl border border-gray-100 px-4 py-3 dark:border-white/5">
                    <p className="truncate text-sm font-medium text-gray-800 dark:text-white/90">{source.title}</p>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {source.source_type} · {source.status}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
