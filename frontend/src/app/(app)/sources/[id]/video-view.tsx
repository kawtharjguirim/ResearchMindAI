"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { AssistantPanel } from "@/components/assistant-panel";
import { Icon } from "@/components/icons";
import { Badge, btnSecondary, card, type Tone } from "@/components/ui";
import { playUrl, videoApi, type AnswerCitation, type Source, type SourceStatus, type TranscriptChunk } from "@/lib/video";

const STATUS: Record<SourceStatus, [string, Tone]> = {
  pending: ["Queued", "gray"],
  transcribing: ["Transcribing", "blue"],
  indexing: ["Indexing", "violet"],
  ready: ["Ready", "green"],
  error: ["Error", "red"],
};

// "hh:mm:ss" -> seconds (also accepts "hh:mm:ss - hh:mm:ss": keeps the start).
function timeToSeconds(ts: string): number {
  const [h, m, s] = ts.split(" - ")[0].split(":").map(Number);
  return h * 3600 + m * 60 + s;
}

export function VideoView({ sourceId }: { sourceId: string }) {
  const [source, setSource] = useState<Source | null>(null);
  const [transcript, setTranscript] = useState<TranscriptChunk[] | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [activeChunk, setActiveChunk] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await videoApi.getSource(sourceId);
        if (cancelled) return;
        setSource(s);
        if (s.status !== "ready") return;
        const [link, chunks] = await Promise.all([videoApi.playLink(sourceId), videoApi.getTranscript(sourceId)]);
        if (cancelled) return;
        setVideoUrl(playUrl(link));
        setTranscript(chunks);
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sourceId]);

  const playAt = useCallback((seconds: number) => {
    const el = videoRef.current;
    if (!el) return;
    el.currentTime = seconds;
    el.play().catch(() => {});
  }, []);

  // Jumped here from the Assistant page with a timestamp, e.g. /sources/{id}#t=125.
  useEffect(() => {
    if (!videoUrl) return;
    const match = /^#t=(\d+(?:\.\d+)?)$/.exec(window.location.hash);
    if (match) playAt(Number(match[1]));
  }, [videoUrl, playAt]);

  function onTimeUpdate() {
    const t = videoRef.current?.currentTime;
    if (t == null || !transcript) return;
    const current = transcript.find((c) => t >= c.start && t < c.end);
    setActiveChunk(current?.chunk_id ?? null);
  }

  function jumpToCitation(citation: AnswerCitation) {
    if (citation.timestamp) playAt(timeToSeconds(citation.timestamp));
  }

  if (error) {
    return (
      <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
        <p className="text-sm text-error-500">{error}</p>
        <Link href="/sources" className={`${btnSecondary} mt-4 inline-flex`}>
          Back to sources
        </Link>
      </div>
    );
  }

  if (!source) {
    return (
      <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
        <div className={`${card} h-64 animate-pulse`} />
      </div>
    );
  }

  const [statusText, statusTone] = STATUS[source.status];

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
          <Icon name="refresh" className="size-6 animate-spin text-primary-500" />
          <p className="mt-4 text-sm text-gray-600 dark:text-gray-300">
            {source.status === "error" ? source.error : "The video is still being processed. Come back once it's ready."}
          </p>
        </div>
      ) : (
        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <div className="space-y-6">
            <div className={`${card} overflow-hidden`}>
              {videoUrl ? (
                // eslint-disable-next-line jsx-a11y/media-has-caption
                <video ref={videoRef} src={videoUrl} controls className="aspect-video w-full bg-black" onTimeUpdate={onTimeUpdate} />
              ) : (
                <div className="aspect-video w-full animate-pulse bg-gray-100 dark:bg-white/10" />
              )}
            </div>

            <div className={`${card} max-h-[60vh] overflow-y-auto p-6`}>
              <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">Transcript</h2>
              {transcript === null ? (
                <div className="mt-4 h-24 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />
              ) : (
                <ol className="mt-4 space-y-1">
                  {transcript.map((c) => (
                    <li key={c.chunk_id}>
                      <button
                        type="button"
                        onClick={() => playAt(c.start)}
                        className={`flex w-full gap-3 rounded-xl px-3 py-2 text-left text-sm transition ${
                          activeChunk === c.chunk_id ? "bg-primary-50 dark:bg-primary-500/10" : "hover:bg-gray-50 dark:hover:bg-white/5"
                        }`}
                      >
                        <span className="shrink-0 font-mono text-xs text-primary-600 dark:text-primary-300">{c.timestamp.split(" - ")[0]}</span>
                        <span className="text-gray-700 dark:text-gray-300">{c.text}</span>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>

          <AssistantPanel
            emptyIcon="chat"
            emptyTitle="Ask a question about this video"
            emptyText="Answers quote the exact sentence of the transcript, with its timestamp. Click a citation to jump to it."
            onAsk={(question) => videoApi.answer(sourceId, question)}
            onJump={jumpToCitation}
          />
        </div>
      )}
    </div>
  );
}
