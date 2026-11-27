"use client";

import Link from "next/link";
import { AssistantPanel } from "@/components/assistant-panel";
import { Icon } from "@/components/icons";
import { Badge, btnSecondary, card, type Tone } from "@/components/ui";
import { videoApi, type AnswerCitation, type Source, type SourceStatus, type TranscriptChunk } from "@/lib/video";

const STATUS: Record<SourceStatus, [string, Tone]> = {
  pending: ["Queued", "gray"],
  transcribing: ["Reading page", "blue"],
  indexing: ["Indexing", "violet"],
  ready: ["Ready", "green"],
  error: ["Error", "red"],
};

// Page web importée par lien : le texte est découpé en passages, et chaque citation renvoie
// vers la page d'origine (une page n'a pas d'horodatage).
export function WebView({ source, passages }: { source: Source; passages: TranscriptChunk[] | null }) {
  const [statusText, statusTone] = STATUS[source.status];

  function openCitation(citation: AnswerCitation) {
    if (citation.url) window.open(citation.url, "_blank", "noopener,noreferrer");
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
      <a href={source.url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block break-all text-sm text-primary-600 hover:underline dark:text-primary-300">
        {source.url}
      </a>

      {source.status !== "ready" ? (
        <div className={`${card} mt-8 flex flex-col items-center px-6 py-14 text-center`}>
          {source.status === "error" ? null : <Icon name="refresh" className="size-6 animate-spin text-primary-500" />}
          <p className="mt-4 text-sm text-gray-600 dark:text-gray-300">
            {source.status === "error" ? source.error : "The page is still being read. Come back once it's ready."}
          </p>
          {source.status === "error" && (
            <Link href="/sources" className={`${btnSecondary} mt-4 inline-flex`}>
              Back to sources
            </Link>
          )}
        </div>
      ) : (
        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <div className={`${card} max-h-[70vh] overflow-y-auto p-6`}>
            <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">Text</h2>
            {passages === null ? (
              <div className="mt-4 h-24 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />
            ) : (
              <ol className="mt-4 space-y-4">
                {passages.map((c) => (
                  <li key={c.chunk_id} className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                    <span className="mb-1 block font-mono text-xs text-primary-600 dark:text-primary-300">{c.timestamp}</span>
                    <p className="whitespace-pre-line">{c.text}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <AssistantPanel
            emptyIcon="chat"
            emptyTitle="Ask a question about this page"
            emptyText="Answers quote the exact sentence of the page. Click a citation to open the page."
            documentId={source.id}
            onAsk={(question) => videoApi.answer(source.id, question)}
            onJump={openCitation}
            linkLabel="open the page"
          />
        </div>
      )}
    </div>
  );
}
