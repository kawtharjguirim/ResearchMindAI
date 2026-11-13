"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AssistantPanel } from "@/components/assistant-panel";
import { btnSecondary, card, inputPill, SourceIcon } from "@/components/ui";
import { videoApi, type AnswerCitation, type Source } from "@/lib/video";

// "hh:mm:ss" (or "hh:mm:ss - hh:mm:ss") -> seconds.
function timeToSeconds(ts: string): number {
  const [h, m, s] = ts.split(" - ")[0].split(":").map(Number);
  return h * 3600 + m * 60 + s;
}

export function AssistantView() {
  const router = useRouter();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [error, setError] = useState("");
  const [sourceId, setSourceId] = useState("");

  useEffect(() => {
    videoApi
      .listSources()
      .then((all) => {
        const ready = all.filter((s) => s.status === "ready");
        setSources(ready);
        if (ready.length > 0) setSourceId(ready[0].id);
      })
      .catch((err) => setError((err as Error).message));
  }, []);

  function jump(citation: AnswerCitation) {
    if (citation.timestamp) {
      router.push(`/sources/${citation.document_id}#t=${timeToSeconds(citation.timestamp)}`);
    } else if (citation.url?.startsWith("/")) {
      router.push(citation.url);
    } else if (citation.url) {
      window.open(citation.url, "_blank", "noopener,noreferrer");
    }
  }

  const selected = sources?.find((s) => s.id === sourceId) ?? null;

  return (
    <div className="mx-auto max-w-[900px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Research assistant</h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        Ask a question about one of your sources. Answers quote the exact passage, with a citation you can jump to.
      </p>

      <div className={`${card} mt-6 p-4`}>
        <label htmlFor="assistant-source" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
          Source
        </label>
        {error ? (
          <div className="text-sm">
            <p className="text-error-500">{error}</p>
            <button type="button" onClick={() => location.reload()} className={`${btnSecondary} mt-3`}>
              Try again
            </button>
          </div>
        ) : sources === null ? (
          <div className="h-12 animate-pulse rounded-full bg-gray-100 dark:bg-white/10" />
        ) : sources.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No ready source yet. Import a video from the Sources page first.</p>
        ) : (
          <div className="relative">
            <select id="assistant-source" className={`${inputPill} appearance-none pl-11`} value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
            {selected && (
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">
                <SourceIcon type={selected.source_type} small />
              </span>
            )}
          </div>
        )}
      </div>

      <div className="mt-6">
        <AssistantPanel
          key={sourceId}
          emptyIcon="chat"
          emptyTitle="Ask a question about your sources"
          emptyText="Select a source above, then ask a question. The answer cites the exact passage and tells you whether it was verified."
          disabled={!sourceId}
          disabledHint="Select a source first"
          documentId={sourceId}
          onAsk={(question) => videoApi.answer(sourceId, question)}
          onJump={jump}
        />
      </div>
    </div>
  );
}
