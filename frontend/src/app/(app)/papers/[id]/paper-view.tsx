"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { Badge, btnSecondary, card, SourceIcon } from "@/components/ui";
import { domainLabel, domainTone, licenseLabel, papersApi, type Paper } from "@/lib/papers";

export function PaperView({ docId, chunkId }: { docId: string; chunkId: string | null }) {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [error, setError] = useState("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    (async () => {
      try {
        const p = await papersApi.get(docId, chunkId);
        if (cancelled) return;
        setPaper(p);
        if (!p.has_pdf) return;
        try {
          const blob = await papersApi.pdf(docId);
          if (cancelled) return;
          objectUrl = URL.createObjectURL(blob);
          setPdfUrl(objectUrl);
        } catch (err) {
          if (!cancelled) setPdfError((err as Error).message);
        }
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [docId, chunkId]);

  // Opened from a citation (chunk given) -> back to the assistant; otherwise from the library.
  const back = (
    <Link href={chunkId ? "/assistant" : "/papers"} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
      <Icon name="arrowLeft" className="size-3.5" />
      {chunkId ? "Back to the assistant" : "Back to the library"}
    </Link>
  );

  if (error) {
    return (
      <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
        {back}
        <p className="mt-4 text-sm text-error-500">{error}</p>
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
        <div className={`${card} h-64 animate-pulse`} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      {back}
      <div className="mt-3 flex items-start gap-3">
        <SourceIcon type="pdf" />
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">{paper.title}</h1>
          {paper.authors && <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{paper.authors}</p>}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <Badge tone={domainTone(paper.domain)}>{domainLabel(paper.domain)}</Badge>
            {paper.categories && <Badge tone="gray">{paper.categories}</Badge>}
            <span>arXiv:{paper.doc_id}</span>
            {paper.update_date && <span>· {paper.update_date}</span>}
            {paper.license && <span>· {licenseLabel(paper.license)}</span>}
            {paper.arxiv_url && (
              <a href={paper.arxiv_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary-600 hover:underline dark:text-primary-300">
                <Icon name="link" className="size-3.5" />
                Open on arXiv
              </a>
            )}
          </div>
        </div>
      </div>

      {chunkId && (
        <div className={`${card} mt-6 p-6`}>
          <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">Cited passage</h2>
          {paper.passage ? (
            <blockquote className="mt-3 border-l-4 border-primary-400 pl-4">
              {paper.passage.section && (
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-primary-600 dark:text-primary-300">{paper.passage.section}</p>
              )}
              <p className="whitespace-pre-line text-sm leading-relaxed text-gray-800 dark:text-white/90">{paper.passage.text}</p>
              <p className="mt-2 text-xs text-gray-400">
                Text extracted from the LaTeX source: citations and formulas may differ from the PDF. Use Ctrl+F in the PDF to find it.
              </p>
            </blockquote>
          ) : (
            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">The cited passage could not be found in this paper.</p>
          )}
        </div>
      )}

      <div className={`${card} mt-6 overflow-hidden`}>
        {!paper.has_pdf ? (
          <p className="p-6 text-sm text-gray-500 dark:text-gray-400">No compiled PDF for this paper.</p>
        ) : pdfError ? (
          <div className="p-6 text-sm">
            <p className="text-error-500">{pdfError}</p>
            <button type="button" onClick={() => location.reload()} className={`${btnSecondary} mt-3`}>
              Try again
            </button>
          </div>
        ) : pdfUrl ? (
          <iframe src={pdfUrl} title={paper.title} className="h-[85vh] w-full bg-gray-100" />
        ) : (
          <div className="h-[85vh] w-full animate-pulse bg-gray-100 dark:bg-white/10" />
        )}
      </div>

      {paper.abstract && (
        <details className={`${card} mt-6 p-6`}>
          <summary className="cursor-pointer text-base font-semibold text-gray-800 dark:text-white/90">Abstract</summary>
          <p className="mt-3 text-sm leading-relaxed text-gray-700 dark:text-gray-300">{paper.abstract}</p>
        </details>
      )}
    </div>
  );
}
