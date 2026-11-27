"use client";

import { useCallback, useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";
import { Badge, btnPrimary, btnSecondary, card, inputPill, SourceIcon, type Tone } from "@/components/ui";
import { api, type Project } from "@/lib/api";
import { VIDEO_EXTENSIONS, videoApi, type Source, type SourceStatus } from "@/lib/video";

const STATUS: Record<SourceStatus, [string, Tone]> = {
  pending: ["Queued", "gray"],
  transcribing: ["Reading", "blue"],
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

// Formats acceptés par la zone de dépôt (le backend vérifie le contenu du fichier).
const DOCUMENT_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".docx", ".md", ".txt"];
const ACCEPTED = [...VIDEO_EXTENSIONS, ...DOCUMENT_EXTENSIONS];

// Filtres de la liste, dans l'ordre affiché.
const FILTRES = [
  { id: "all", label: "All" },
  { id: "pdf", label: "PDF" },
  { id: "web", label: "Web" },
  { id: "figure", label: "Figures" },
  { id: "video", label: "Videos" },
  { id: "personal", label: "Personal documents" },
] as const;
type Filtre = (typeof FILTRES)[number]["id"];

const POLL_MS = 3000;
const label = "mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300";

function duration(sec: number | null) {
  if (sec == null) return null;
  const s = Math.round(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min ${String(s % 60).padStart(2, "0")}`;
}

// Origin shown in the table: the link's domain, or the kind of file.
function origine(s: Source): string {
  if (s.url) {
    try {
      return new URL(s.url).hostname.replace(/^www\./, "");
    } catch {
      // Not a valid address: fall back to the file kind.
    }
  }
  const types: Record<string, string> = {
    video: "Video file",
    pdf: "PDF file",
    web: "Web page",
    figure: "Image",
    personal: "Personal document",
  };
  return types[s.source_type] ?? "—";
}

function dateCourte(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function UploadCard({ projects, onUploaded }: { projects: Project[]; onUploaded: (s: Source) => void }) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("fr");
  const [projectId, setProjectId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // The file type comes from its extension; the backend then checks the content.
  const estDocument = (f: File) => DOCUMENT_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext));

  function choisir(f: File | null | undefined) {
    if (!f) return;
    setFile(f);
    setError("");
  }

  function depose(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    choisir(e.dataTransfer.files?.[0]);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const source = estDocument(file)
        ? await videoApi.uploadDocument({ file, title, projectId: projectId || undefined })
        : await videoApi.uploadVideo({ file, title, language, projectId: projectId || undefined });
      onUploaded(source);
      toast(estDocument(file) ? "File imported: text is being read" : "Video imported: transcription started");
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
    <form onSubmit={submit} className={`${card} flex flex-col p-6`}>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={depose}
        onClick={() => fileRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") fileRef.current?.click();
        }}
        className={`flex min-h-[220px] cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-8 text-center transition ${
          dragging
            ? "border-primary-400 bg-primary-50 dark:bg-primary-500/10"
            : "border-primary-200 bg-primary-50/60 hover:border-primary-300 dark:border-primary-500/30 dark:bg-white/5"
        }`}
      >
        <span className="flex size-14 items-center justify-center rounded-full bg-white shadow-sm dark:bg-white/10">
          <Icon name="upload" className="size-6 text-primary-500" />
        </span>
        {file ? (
          <>
            <p className="max-w-full truncate text-sm font-medium text-gray-800 dark:text-white/90">{file.name}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{(file.size / 1024 ** 2).toFixed(1)} MB</p>
          </>
        ) : (
          <>
            <p className="text-sm text-gray-800 dark:text-white/90">
              Drag your files here or <span className="font-medium text-primary-600 dark:text-primary-300">browse</span>
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Accepted formats: PDF, PNG, JPG, {VIDEO_EXTENSIONS.map((x) => x.slice(1).toUpperCase()).join(", ")}</p>
          </>
        )}
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED.join(",")}
          className="sr-only"
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => choisir(e.target.files?.[0])}
        />
      </div>

      {file && (
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor="file-title" className={label}>
              Title <span className="font-normal text-gray-400">(optional)</span>
            </label>
            <input id="file-title" className={inputPill} value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} placeholder={file.name.replace(/\.[^.]+$/, "")} />
          </div>
          {!estDocument(file) && (
            <div>
              <label htmlFor="file-language" className={label}>
                Spoken language
              </label>
              <select id="file-language" className={inputPill} value={language} onChange={(e) => setLanguage(e.target.value)}>
                {LANGUAGES.map(([code, name]) => (
                  <option key={code} value={code}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className={estDocument(file) ? "sm:col-span-2" : ""}>
            <label htmlFor="file-project" className={label}>
              Project <span className="font-normal text-gray-400">(optional)</span>
            </label>
            <select id="file-project" className={inputPill} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">No project</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {error && <p className="mt-4 text-sm text-error-500">{error}</p>}
      <button type="submit" disabled={!file || busy} className={`${btnPrimary} mt-5 w-full disabled:opacity-50`}>
        <Icon name={busy ? "refresh" : "plus"} className={`size-4 ${busy ? "animate-spin" : ""}`} />
        {busy ? "Importing…" : "Import"}
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
      toast("Link added: its content is being read");
      setUrl("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className={`${card} flex flex-col p-6`}>
      <div className="flex items-center gap-3">
        <SourceIcon type="web" />
        <div>
          <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">Paste a URL (web page or YouTube video)</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">Videos are transcribed with timestamps, so citations point to the exact second.</p>
        </div>
      </div>

      <div className="mt-5">
        <label htmlFor="source-url" className={label}>
          Link
        </label>
        <input id="source-url" type="url" className={inputPill} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." />
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
      <button type="submit" disabled={!url.trim() || busy} className={`${btnPrimary} mt-auto w-full disabled:opacity-50`}>
        <Icon name={busy ? "refresh" : "plus"} className={`size-4 ${busy ? "animate-spin" : ""}`} />
        {busy ? "Adding…" : "Add"}
      </button>
    </form>
  );
}

function SourceTableRow({ s, onDelete }: { s: Source; onDelete: () => void }) {
  const [text, tone] = STATUS[s.status];
  const working = s.status === "pending" || s.status === "transcribing" || s.status === "indexing";
  // Imported sources (video, web page, PDF, image): openable once ready, and deletable.
  const stockee = ["video", "web", "pdf", "figure", "personal"].includes(s.source_type);
  const canOpen = stockee && s.status === "ready";
  const detail = [duration(s.duration), s.chunk_count ? `${s.chunk_count} passages` : null].filter(Boolean).join(" · ");

  return (
    <tr className="border-t border-gray-100 align-top dark:border-white/5">
      <td className="py-3 pr-4">
        <div className="flex items-center gap-3">
          <SourceIcon type={s.source_type} small />
          {canOpen ? (
            <Link href={`/sources/${s.id}`} className="truncate text-sm font-medium text-gray-800 hover:text-primary-600 dark:text-white/90">
              {s.title}
            </Link>
          ) : (
            <span className="truncate text-sm font-medium text-gray-800 dark:text-white/90">{s.title}</span>
          )}
        </div>
        {s.status === "error" && <p className="mt-1.5 break-words text-xs text-error-500">{s.error}</p>}
        {s.excerpt && <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">{s.excerpt}</p>}
      </td>
      <td className="py-3 pr-4 text-sm text-gray-500 dark:text-gray-400">{origine(s)}</td>
      <td className="whitespace-nowrap py-3 pr-4 text-sm text-gray-500 dark:text-gray-400">{dateCourte(s.created_at)}</td>
      <td className="whitespace-nowrap py-3 pr-4 text-sm text-gray-500 dark:text-gray-400">{detail || "—"}</td>
      <td className="py-3 pr-4">
        <Badge tone={tone}>
          {working && <Icon name="refresh" className="size-3 animate-spin" />}
          {text}
        </Badge>
      </td>
      <td className="py-3 text-right">
        {stockee && (
          <button type="button" onClick={onDelete} className="rounded-full p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-error-500 dark:hover:bg-white/10" aria-label={`Delete ${s.title}`}>
            <Icon name="x" className="size-4" />
          </button>
        )}
      </td>
    </tr>
  );
}

export function SourcesView() {
  const toast = useToast();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [filtre, setFiltre] = useState<Filtre>("all");
  const [recherche, setRecherche] = useState("");

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

  // Follow processing: poll while a source is still being read, transcribed or indexed.
  const working = sources?.some((s) => s.status !== "ready" && s.status !== "error");
  useEffect(() => {
    if (!working) return;
    const t = setInterval(() => videoApi.listSources().then(setSources).catch(() => {}), POLL_MS);
    return () => clearInterval(t);
  }, [working]);

  async function remove(s: Source) {
    if (!window.confirm(`Delete "${s.title}" and its content?`)) return;
    try {
      await videoApi.deleteSource(s.id);
      setSources((list) => list?.filter((x) => x.id !== s.id) ?? null);
      toast("Source deleted");
    } catch (err) {
      toast((err as Error).message, false);
    }
  }

  const compte = (id: Filtre) => (id === "all" ? sources?.length ?? 0 : sources?.filter((s) => s.source_type === id).length ?? 0);
  const affichees = (sources ?? []).filter(
    (s) => (filtre === "all" || s.source_type === filtre) && s.title.toLowerCase().includes(recherche.trim().toLowerCase()),
  );

  return (
    <div className="mx-auto max-w-[1100px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Project sources</h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Import videos, PDFs, images, Word, Markdown or text files, then follow their processing. Ask questions from the Assistant page.</p>

      <div className="mt-8 space-y-6">
        <div className="grid items-stretch gap-6 lg:grid-cols-2">
          <UploadCard projects={projects} onUploaded={(s) => setSources((list) => [s, ...(list ?? [])])} />
          <UrlCard projects={projects} onImported={(s) => setSources((list) => [s, ...(list ?? [])])} />
        </div>

        <div className={`${card} p-6`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {FILTRES.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFiltre(f.id)}
                  className={`rounded-full px-4 py-1.5 text-sm transition ${
                    filtre === f.id
                      ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                      : "border border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-white/10 dark:text-gray-300 dark:hover:bg-white/5"
                  }`}
                >
                  {f.label}
                  {sources && ` (${compte(f.id)})`}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <input
                type="search"
                value={recherche}
                onChange={(e) => setRecherche(e.target.value)}
                placeholder="Search sources"
                className={`${inputPill} w-56`}
              />
              <button type="button" onClick={load} className="rounded-full p-1.5 text-gray-400 transition hover:bg-gray-100 dark:hover:bg-white/10" aria-label="Refresh">
                <Icon name="refresh" className="size-4" />
              </button>
            </div>
          </div>

          {error ? (
            <div className="mt-6 text-sm">
              <p className="text-error-500">{error}</p>
              <button type="button" onClick={load} className={`${btnSecondary} mt-3`}>
                Try again
              </button>
            </div>
          ) : sources === null ? (
            <div className="mt-6 h-16 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />
          ) : sources.length === 0 ? (
            <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">No source yet: import a video, a document or an image above.</p>
          ) : affichees.length === 0 ? (
            <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">No source matches this filter or search.</p>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left">
                <thead>
                  <tr className="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
                    <th className="pb-2 pr-4 font-medium">Source</th>
                    <th className="pb-2 pr-4 font-medium">Origin</th>
                    <th className="pb-2 pr-4 font-medium">Added</th>
                    <th className="pb-2 pr-4 font-medium">Details</th>
                    <th className="pb-2 pr-4 font-medium">Status</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {affichees.map((s) => (
                    <SourceTableRow key={s.id} s={s} onDelete={() => remove(s)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
