"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import { Badge, btnSecondary, card, inputPill } from "@/components/ui";
import { DOMAINS, domainLabel, domainTone, licenseLabel, papersApi, type PaperSummary } from "@/lib/papers";

type Sort = "title" | "newest" | "oldest";

// Lowercase without accents, so "modele" finds "modèle".
const fold = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

function StatCard({ icon, value, label }: { icon: Parameters<typeof Icon>[0]["name"]; value: string | number; label: string }) {
  return (
    <div className={`${card} flex items-center gap-4 p-5`}>
      <span className="inline-flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-500 dark:bg-primary-500/15">
        <Icon name={icon} className="size-5" />
      </span>
      <div>
        <p className="text-2xl font-semibold text-gray-800 dark:text-white/90">{value}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      </div>
    </div>
  );
}

function PaperCard({ p }: { p: PaperSummary }) {
  return (
    <Link
      href={`/papers/${encodeURIComponent(p.doc_id)}`}
      className={`${card} group flex flex-col p-5 transition hover:-translate-y-0.5 hover:border-primary-300 dark:hover:border-primary-500/40`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge tone={domainTone(p.domain)}>{domainLabel(p.domain)}</Badge>
          {p.update_date && <span className="text-xs text-gray-400">{p.update_date.slice(0, 4)}</span>}
        </div>
        {p.has_pdf && (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-400" title="PDF available">
            <Icon name="pdf" className="size-3.5" />
            PDF
          </span>
        )}
      </div>

      <h2 className="mt-3 line-clamp-2 text-base font-semibold leading-snug text-gray-800 transition group-hover:text-primary-600 dark:text-white/90 dark:group-hover:text-primary-300">
        {p.title}
      </h2>
      {p.authors && <p className="mt-1 line-clamp-1 text-xs text-gray-500 dark:text-gray-400">{p.authors}</p>}
      {p.abstract && <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-gray-600 dark:text-gray-300">{p.abstract}</p>}

      <div className="min-h-4 flex-1" />
      <div className="flex items-center justify-between gap-2 border-t border-gray-100 pt-4 text-xs text-gray-500 dark:border-white/5 dark:text-gray-400">
        <span className="truncate">
          arXiv:{p.doc_id} · {licenseLabel(p.license)}
        </span>
        <span className="inline-flex shrink-0 items-center gap-1 font-medium text-primary-600 dark:text-primary-300">
          Read
          <Icon name="arrowLeft" className="size-3.5 rotate-180" />
        </span>
      </div>
    </Link>
  );
}

export function LibraryView() {
  const [papers, setPapers] = useState<PaperSummary[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>("title");

  const load = useCallback(async () => {
    setError("");
    try {
      setPapers(await papersApi.list());
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const p of papers ?? []) c[p.domain] = (c[p.domain] ?? 0) + 1;
    return c;
  }, [papers]);

  const shown = useMemo(() => {
    const q = fold(query.trim());
    const list = (papers ?? []).filter(
      (p) =>
        (!domain || p.domain === domain) &&
        (!q || fold(`${p.title} ${p.authors} ${p.abstract} ${p.doc_id} ${p.categories}`).includes(q)),
    );
    if (sort === "title") return list;
    const dir = sort === "newest" ? -1 : 1;
    return [...list].sort((a, b) => dir * a.update_date.localeCompare(b.update_date));
  }, [papers, query, domain, sort]);

  const domainKeys = Object.keys(DOMAINS).filter((k) => counts[k]);
  const chip = (active: boolean) =>
    `inline-flex h-9 items-center gap-1.5 rounded-full px-4 text-sm font-medium transition ${
      active
        ? "bg-primary-500 text-white shadow-theme-xs"
        : "border border-gray-200 bg-white text-gray-600 hover:border-primary-300 hover:text-primary-600 dark:border-gray-700 dark:bg-white/5 dark:text-gray-300"
    }`;

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Library</h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        The open-access arXiv papers indexed for the research assistant. Open one to read its PDF.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <StatCard icon="book" value={papers?.length ?? "—"} label="Papers" />
        <StatCard icon="layers" value={papers ? domainKeys.length : "—"} label="Domains" />
        <StatCard icon="shield" value="CC BY · CC0" label="Open licenses only" />
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Icon name="search" className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
          <input
            className={`${inputPill} pl-11`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title, author, abstract or arXiv id…"
            aria-label="Search the library"
          />
        </div>
        <select className={`${inputPill} sm:w-48`} value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort">
          <option value="title">Title (A–Z)</option>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </div>

      {papers && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className={chip(domain === null)} onClick={() => setDomain(null)}>
            All <span className="opacity-70">{papers.length}</span>
          </button>
          {domainKeys.map((k) => (
            <button key={k} type="button" className={chip(domain === k)} onClick={() => setDomain(domain === k ? null : k)}>
              {domainLabel(k)} <span className="opacity-70">{counts[k]}</span>
            </button>
          ))}
        </div>
      )}

      {error ? (
        <div className={`${card} mt-6 p-6 text-sm`}>
          <p className="text-error-500">{error}</p>
          <button type="button" onClick={load} className={`${btnSecondary} mt-3`}>
            Try again
          </button>
        </div>
      ) : papers === null ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className={`${card} h-56 animate-pulse`} />
          ))}
        </div>
      ) : shown.length === 0 ? (
        <div className={`${card} mt-6 flex flex-col items-center px-6 py-14 text-center`}>
          <span className="inline-flex size-12 items-center justify-center rounded-full bg-primary-50 text-primary-500 dark:bg-primary-500/15">
            <Icon name="search" className="size-6" />
          </span>
          <p className="mt-4 font-semibold text-gray-800 dark:text-white/90">No paper matches your search</p>
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setDomain(null);
            }}
            className={`${btnSecondary} mt-4`}
          >
            Clear filters
          </button>
        </div>
      ) : (
        <>
          <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
            {shown.length === papers.length ? `${papers.length} papers` : `${shown.length} of ${papers.length} papers`}
          </p>
          <div className="mt-3 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {shown.map((p) => (
              <PaperCard key={p.doc_id} p={p} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
