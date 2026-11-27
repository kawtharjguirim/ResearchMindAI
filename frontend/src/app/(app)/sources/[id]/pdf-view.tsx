"use client";

import Link from "next/link";
import { useState } from "react";
import { AssistantPanel } from "@/components/assistant-panel";
import { Icon } from "@/components/icons";
import { Badge, btnSecondary, card, type Tone } from "@/components/ui";
import { videoApi, type AnswerCitation, type Source, type SourceStatus, type TranscriptChunk } from "@/lib/video";

const STATUS: Record<SourceStatus, [string, Tone]> = {
  pending: ["Queued", "gray"],
  transcribing: ["Reading document", "blue"],
  indexing: ["Indexing", "violet"],
  ready: ["Ready", "green"],
  error: ["Error", "red"],
};

// "p. 3" -> 3 (étiquette de page des passages et des citations).
function pageOf(label: string | null | undefined): number | null {
  const m = /p\. (\d+)/.exec(label ?? "");
  return m ? Number(m[1]) : null;
}

// PDF importé : le fichier s'affiche à la page choisie ; passages et citations y renvoient.
export function PdfView({ source, passages, fileUrl }: { source: Source; passages: TranscriptChunk[] | null; fileUrl: string | null }) {
  const [statusText, statusTone] = STATUS[source.status];
  const [page, setPage] = useState(1);

  function jumpToCitation(citation: AnswerCitation) {
    const n = pageOf(citation.timestamp);
    if (n) setPage(n);
  }

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      <Link href="/sources" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
        <Icon name="arrowLeft" className="size-3.5" />
        Back to sources
      </Link>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">{source.title}</h1>
        <Badge tone={statusTone}>{statusText}</Badge>
      </div>

      {source.status !== "ready" ? (
        <div className={`${card} mt-8 flex flex-col items-center px-6 py-14 text-center`}>
          {source.status === "error" ? null : <Icon name="refresh" className="size-6 animate-spin text-primary-500" />}
          <p className="mt-4 text-sm text-gray-600 dark:text-gray-300">
            {source.status === "error" ? source.error : "The document is still being read. Come back once it's ready."}
          </p>
          {source.status === "error" && (
            <Link href="/sources" className={`${btnSecondary} mt-4 inline-flex`}>
              Back to sources
            </Link>
          )}
        </div>
      ) : (
        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <div className="space-y-6">
            <div className={`${card} overflow-hidden`}>
              {fileUrl ? (
                <iframe title={source.title} src={`${fileUrl}#page=${page}`} className="h-[70vh] w-full bg-gray-100 dark:bg-white/10" />
              ) : (
                <div className="h-[70vh] w-full animate-pulse bg-gray-100 dark:bg-white/10" />
              )}
            </div>

            <div className={`${card} max-h-[40vh] overflow-y-auto p-6`}>
              <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">Passages</h2>
              {passages === null ? (
                <div className="mt-4 h-24 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />
              ) : (
                <ol className="mt-4 space-y-3">
                  {passages.map((c) => (
                    <li key={c.chunk_id}>
                      <button
                        type="button"
                        onClick={() => pageOf(c.timestamp) && setPage(pageOf(c.timestamp) as number)}
                        className="flex w-full gap-3 rounded-xl px-3 py-2 text-left text-sm transition hover:bg-gray-50 dark:hover:bg-white/5"
                      >
                        <span className="shrink-0 font-mono text-xs text-primary-600 dark:text-primary-300">{c.timestamp}</span>
                        <span className="whitespace-pre-line text-gray-700 dark:text-gray-300">{c.text}</span>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>

          <AssistantPanel
            emptyIcon="chat"
            emptyTitle="Ask a question about this document"
            emptyText="Answers quote the exact sentence of the document, with its page. Click a citation to open that page."
            documentId={source.id}
            onAsk={(question) => videoApi.answer(source.id, question)}
            onJump={jumpToCitation}
          />
        </div>
      )}
    </div>
  );
}
