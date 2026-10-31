"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";
import { Badge, btnPrimary, btnSecondary, card, inputPill, SourceIcon, type Tone } from "@/components/ui";
import { api, type Project } from "@/lib/api";
import { VIDEO_EXTENSIONS, videoApi, type AskResponse, type AskStatus, type Source, type SourceStatus } from "@/lib/video";

const STATUS: Record<SourceStatus, [string, Tone]> = {
  pending: ["Queued", "gray"],
  transcribing: ["Transcribing", "blue"],
  indexing: ["Indexing", "violet"],
  ready: ["Ready", "green"],
  error: ["Error", "red"],
};

const ANSWER: Record<AskStatus, [string, Tone]> = {
  repondu: ["Answer found", "green"],
  confiance_faible: ["Low confidence: check the passages", "orange"],
  hors_sujet: ["Not in the video", "gray"],
};

const LANGUAGES = [
  ["fr", "French"],
  ["en", "English"],
  ["es", "Spanish"],
  ["de", "German"],
] as const;

const POLL_MS = 3000;
const label = "mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300";

function duration(sec: number | null) {
  if (sec == null) return null;
  const s = Math.round(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min ${String(s % 60).padStart(2, "0")}`;
}

function UploadCard({ projects, onUploaded }: { projects: Project[]; onUploaded: (s: Source) => void }) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("fr");
  const [projectId, setProjectId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const source = await videoApi.uploadVideo({ file, title, language, projectId: projectId || undefined });
      onUploaded(source);
      toast("Video imported: transcription started");
      setFile(null);
      setTitle("");
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className={`${card} p-6`}>
      <div className="flex items-center gap-3">
        <SourceIcon type="video" />
        <div>
          <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">Import a video</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">Transcribed locally, then indexed for questions</p>
        </div>
      </div>

      <label className="mt-5 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-200 px-4 py-6 text-center text-sm text-gray-500 transition hover:border-primary-300 dark:border-gray-700 dark:text-gray-400">
        <Icon name="video" className="size-6 text-primary-500" />
        <span className="font-medium text-gray-700 dark:text-gray-300">{file ? file.name : "Choose a video file"}</span>
        <span className="text-xs">
          {file ? `${(file.size / 1024 ** 2).toFixed(0)} MB` : VIDEO_EXTENSIONS.join(", ")}
        </span>
        <input
          ref={fileRef}
          type="file"
          accept={VIDEO_EXTENSIONS.join(",")}
          className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label htmlFor="video-title" className={label}>
            Title <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <input id="video-title" className={inputPill} value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} placeholder={file?.name.replace(/\.[^.]+$/, "") ?? "Lecture title"} />
        </div>
        <div>
          <label htmlFor="video-language" className={label}>
            Spoken language
          </label>
          <select id="video-language" className={inputPill} value={language} onChange={(e) => setLanguage(e.target.value)}>
            {LANGUAGES.map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="video-project" className={label}>
            Project <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <select id="video-project" className={inputPill} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">No project</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="mt-4 text-sm text-error-500">{error}</p>}
      <button type="submit" disabled={!file || busy} className={`${btnPrimary} mt-5 w-full disabled:opacity-50`}>
        <Icon name={busy ? "refresh" : "plus"} className={`size-4 ${busy ? "animate-spin" : ""}`} />
        {busy ? "Uploading…" : "Import the video"}
      </button>
    </form>
  );
}

function SourceRow({ s, selected, onSelect, onDelete }: { s: Source; selected: boolean; onSelect: () => void; onDelete: () => void }) {
  const [text, tone] = STATUS[s.status];
  const working = s.status === "pending" || s.status === "transcribing" || s.status === "indexing";
  const meta = [duration(s.duration), s.language?.toUpperCase(), s.chunk_count ? `${s.chunk_count} passages` : null].filter(Boolean);
  return (
    <li
      className={`flex items-start gap-3 rounded-2xl border p-4 transition ${
        selected ? "border-primary-300 bg-primary-50/50 dark:border-primary-500/40 dark:bg-primary-500/5" : "border-gray-100 dark:border-white/5"
      }`}
    >
      <SourceIcon type="video" small />
      <button type="button" onClick={onSelect} disabled={s.status !== "ready"} className="min-w-0 flex-1 text-left disabled:cursor-default">
        <p className="truncate text-sm font-medium text-gray-800 dark:text-white/90">{s.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Badge tone={tone}>
            {working && <Icon name="refresh" className="size-3 animate-spin" />}
            {text}
          </Badge>
          {meta.join(" · ")}
        </div>
        {s.status === "error" && <p className="mt-2 break-words text-xs text-error-500">{s.error}</p>}
      </button>
      <button type="button" onClick={onDelete} className="rounded-full p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-error-500 dark:hover:bg-white/10" aria-label={`Delete ${s.title}`}>
        <Icon name="x" className="size-4" />
      </button>
    </li>
  );
}

function AskPanel({ source }: { source: Source | null }) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);

  useEffect(() => {
    setAnswer(null);
    setError("");
  }, [source?.id]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!source || !question.trim()) return;
    setBusy(true);
    setError("");
    try {
      setAnswer(await videoApi.ask(source.id, question.trim()));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!source) {
    return (
      <div className={`${card} flex flex-col items-center px-6 py-14 text-center`}>
        <span className="inline-flex size-12 items-center justify-center rounded-full bg-primary-50 text-primary-500 dark:bg-primary-500/15">
          <Icon name="chat" className="size-6" />
        </span>
        <p className="mt-4 font-semibold text-gray-800 dark:text-white/90">Ask a question about a video</p>
        <p className="mt-1 max-w-sm text-sm text-gray-500 dark:text-gray-400">
          Select a ready video. Answers quote the exact sentence of the transcript, with its timestamp.
        </p>
      </div>
    );
  }

  const [answerLabel, answerTone] = answer ? ANSWER[answer.status] : ["", "gray" as Tone];
  return (
    <div className={`${card} p-6`}>
      <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Asking</p>
      <h2 className="mt-1 text-base font-semibold text-gray-800 dark:text-white/90">{source.title}</h2>

      <form onSubmit={submit} className="mt-4 flex gap-2">
        <input
          className={inputPill}
          value={question}
          maxLength={1000}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What does the video say about…?"
          aria-label="Question"
        />
        <button type="submit" disabled={busy || !question.trim()} className={`${btnPrimary} h-12 shrink-0 disabled:opacity-50`}>
          {busy ? <Icon name="refresh" className="size-4 animate-spin" /> : "Ask"}
        </button>
      </form>
      {busy && <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">Searching the transcript and checking the answer…</p>}
      {error && <p className="mt-3 text-sm text-error-500">{error}</p>}

      {answer && (
        <div className="mt-6">
          <Badge tone={answerTone}>{answerLabel}</Badge>
          {answer.citation ? (
            <blockquote className="mt-4 border-l-4 border-primary-400 pl-4">
              <p className="text-sm leading-relaxed text-gray-800 dark:text-white/90">« {answer.citation.text} »</p>
              <p className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-300">
                <Icon name="clock" className="size-3.5" />
                {answer.citation.timestamp}
              </p>
            </blockquote>
          ) : (
            <p className="mt-4 text-sm text-gray-700 dark:text-gray-300">{answer.answer}</p>
          )}
          {answer.rephrasing && <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">{answer.rephrasing}</p>}

          {answer.passages.length > 0 && (
            <details className="mt-6" open={answer.status !== "repondu"}>
              <summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">
                Passages read ({answer.passages.length})
              </summary>
              <ol className="mt-3 space-y-3">
                {answer.passages.map((p, i) => (
                  <li key={p.chunk_id} className={`rounded-xl p-3 text-sm ${answer.citation?.passage === i + 1 ? "bg-primary-50 dark:bg-primary-500/10" : "bg-gray-50 dark:bg-white/5"}`}>
                    <div className="mb-1 flex justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span className="font-medium">{p.timestamp}</span>
                      <span title="Reranker relevance score">score {p.rerank.toFixed(3)}</span>
                    </div>
                    <p className="line-clamp-4 text-gray-700 dark:text-gray-300">{p.text}</p>
                  </li>
                ))}
              </ol>
            </details>
          )}
          <p className="mt-4 text-xs text-gray-400">
            {Object.entries(answer.timings)
              .map(([k, v]) => `${k} ${v.toFixed(1)} s`)
              .join(" · ")}
          </p>
        </div>
      )}
    </div>
  );
}

export function SourcesView() {
  const toast = useToast();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setSources(await videoApi.listSources());
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
    api.listProjects().then(setProjects).catch(() => setProjects([]));
  }, [load]);

  // Follow processing: poll while a video is still being transcribed or indexed.
  const working = sources?.some((s) => s.status !== "ready" && s.status !== "error");
  useEffect(() => {
    if (!working) return;
    const t = setInterval(() => videoApi.listSources().then(setSources).catch(() => {}), POLL_MS);
    return () => clearInterval(t);
  }, [working]);

  async function remove(s: Source) {
    if (!window.confirm(`Delete "${s.title}" and its transcript?`)) return;
    try {
      await videoApi.deleteSource(s.id);
      setSources((list) => list?.filter((x) => x.id !== s.id) ?? null);
      if (selectedId === s.id) setSelectedId(null);
      toast("Video deleted");
    } catch (err) {
      toast((err as Error).message, false);
    }
  }

  const selected = sources?.find((s) => s.id === selectedId && s.status === "ready") ?? null;

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Project sources</h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Import videos, follow their transcription and ask questions about them</p>

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="space-y-6">
          <UploadCard projects={projects} onUploaded={(s) => setSources((list) => [s, ...(list ?? [])])} />

          <div className={`${card} p-6`}>
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">My videos</h2>
              <button type="button" onClick={load} className="rounded-full p-1.5 text-gray-400 transition hover:bg-gray-100 dark:hover:bg-white/10" aria-label="Refresh">
                <Icon name="refresh" className="size-4" />
              </button>
            </div>
            {error ? (
              <div className="mt-4 text-sm">
                <p className="text-error-500">{error}</p>
                <button type="button" onClick={load} className={`${btnSecondary} mt-3`}>
                  Try again
                </button>
              </div>
            ) : sources === null ? (
              <div className="mt-4 h-16 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />
            ) : sources.length === 0 ? (
              <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">No video yet: import one above.</p>
            ) : (
              <ul className="mt-4 space-y-3">
                {sources.map((s) => (
                  <SourceRow key={s.id} s={s} selected={s.id === selected?.id} onSelect={() => setSelectedId(s.id)} onDelete={() => remove(s)} />
                ))}
              </ul>
            )}
          </div>
        </div>

        <AskPanel source={selected} />
      </div>
    </div>
  );
}
