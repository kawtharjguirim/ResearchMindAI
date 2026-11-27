"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";
import { Badge, btnPrimary, btnSecondary, card, inputPill, SourceIcon, type Tone } from "@/components/ui";
import { api, type Project } from "@/lib/api";
import { VIDEO_EXTENSIONS, videoApi, type Source, type SourceStatus } from "@/lib/video";

const STATUS: Record<SourceStatus, [string, Tone]> = {
  pending: ["Queued", "gray"],
  transcribing: ["Transcribing", "blue"],
  indexing: ["Indexing", "violet"],
  ready: ["Ready", "green"],
  error: ["Error", "red"],
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

function UrlCard({ projects, onImported }: { projects: Project[]; onImported: (s: Source) => void }) {
  const toast = useToast();
  const [url, setUrl] = useState("");
  const [projectId, setProjectId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setBusy(true);
    setError("");
    try {
      const source = await videoApi.importUrl({ url, projectId: projectId || undefined });
      onImported(source);
      toast("YouTube link added: subtitles are being read");
      setUrl("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className={`${card} p-6`}>
      <div className="flex items-center gap-3">
        <SourceIcon type="web" />
        <div>
          <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">Coller une URL (page web ou vidéo YouTube)</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">Les vidéos sont transcrites avec leurs timestamps pour être citées à la seconde près.</p>
        </div>
      </div>

      <div className="mt-5">
        <label htmlFor="source-url" className={label}>
          Lien
        </label>
        <input
          id="source-url"
          type="url"
          className={inputPill}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://..."
        />
      </div>

      <div className="mt-4">
        <label htmlFor="url-project" className={label}>
          Project <span className="font-normal text-gray-400">(optional)</span>
        </label>
        <select id="url-project" className={inputPill} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">No project</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="mt-4 text-sm text-error-500">{error}</p>}
      <button type="submit" disabled={!url.trim() || busy} className={`${btnPrimary} mt-5 w-full disabled:opacity-50`}>
        <Icon name={busy ? "refresh" : "plus"} className={`size-4 ${busy ? "animate-spin" : ""}`} />
        {busy ? "Ajout…" : "Ajouter"}
      </button>
    </form>
  );
}

function SourceRow({ s, onDelete }: { s: Source; onDelete: () => void }) {
  const [text, tone] = STATUS[s.status];
  const working = s.status === "pending" || s.status === "transcribing" || s.status === "indexing";
  const meta = [duration(s.duration), s.language?.toUpperCase(), s.chunk_count ? `${s.chunk_count} passages` : null].filter(Boolean);
  // Sources importées (vidéo ou lien) : ouvrables une fois prêtes et supprimables.
  const isVideo = s.source_type === "video" || s.source_type === "web";
  const canOpen = isVideo && s.status === "ready";

  const content = (
    <>
      <SourceIcon type={s.source_type} small />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-800 dark:text-white/90">{s.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Badge tone={tone}>
            {working && <Icon name="refresh" className="size-3 animate-spin" />}
            {text}
          </Badge>
          {meta.join(" · ")}
        </div>
        {s.status === "error" && <p className="mt-2 break-words text-xs text-error-500">{s.error}</p>}
        {s.excerpt && <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">{s.excerpt}</p>}
      </div>
    </>
  );

  return (
    <li className="flex items-start gap-3 rounded-2xl border border-gray-100 p-4 transition dark:border-white/5">
      {canOpen ? (
        <Link href={`/sources/${s.id}`} className="flex min-w-0 flex-1 items-start gap-3 text-left">
          {content}
        </Link>
      ) : (
        <div className="flex min-w-0 flex-1 items-start gap-3">{content}</div>
      )}
      {isVideo && (
        <button type="button" onClick={onDelete} className="rounded-full p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-error-500 dark:hover:bg-white/10" aria-label={`Delete ${s.title}`}>
          <Icon name="x" className="size-4" />
        </button>
      )}
    </li>
  );
}

export function SourcesView() {
  const toast = useToast();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
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
      toast("Video deleted");
    } catch (err) {
      toast((err as Error).message, false);
    }
  }

  return (
    <div className="mx-auto max-w-[800px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Project sources</h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Import videos and follow their transcription. Ask questions from the Assistant page.</p>

      <div className="mt-8 space-y-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <UploadCard projects={projects} onUploaded={(s) => setSources((list) => [s, ...(list ?? [])])} />
          <UrlCard projects={projects} onImported={(s) => setSources((list) => [s, ...(list ?? [])])} />
        </div>

        <div className={`${card} p-6`}>
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">My sources</h2>
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
            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">No source yet: import a video above.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {sources.map((s) => (
                <SourceRow key={s.id} s={s} onDelete={() => remove(s)} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
