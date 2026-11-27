"use client";

import Link from "next/link";
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

// Document personnel (Word, Markdown ou texte) : le texte est découpé en passages ; le fichier
// d'origine s'ouvre dans un nouvel onglet, car ces formats n'ont ni pages ni horodatage.
export function PersonalView({ source, passages, fileUrl }: { source: Source; passages: TranscriptChunk[] | null; fileUrl: string | null }) {
  const [statusText, statusTone] = STATUS[source.status];

  function ouvrirFichier(_citation?: AnswerCitation) {
    if (fileUrl) window.open(fileUrl, "_blank", "noopener,noreferrer");
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
            <div className={`${card} flex items-center justify-between gap-4 p-6`}>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-gray-800 dark:text-white/90">{source.title}</p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{passages ? `${passages.length} passages` : " "}</p>
              </div>
              <button
                type="button"
                onClick={() => ouvrirFichier()}
                disabled={!fileUrl}
                className={`${btnSecondary} shrink-0 disabled:opacity-50`}
              >
                <Icon name="link" className="size-4" />
                Open file
              </button>
            </div>

            <div className={`${card} max-h-[60vh] overflow-y-auto p-6`}>
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
          </div>

          <AssistantPanel
            emptyIcon="chat"
            emptyTitle="Ask a question about this document"
            emptyText="Answers quote the exact sentence of the document. Click a citation to open the file."
            documentId={source.id}
            onAsk={(question) => videoApi.answer(source.id, question)}
            onJump={ouvrirFichier}
          />
        </div>
      )}
    </div>
  );
}
