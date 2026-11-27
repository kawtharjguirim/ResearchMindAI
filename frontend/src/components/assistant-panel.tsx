"use client";

// Generic question/answer panel, reused by the Assistant page (all sources) and the Video
// page (one video): chat-style question bubble, status badge, clickable citation, "passages
// used" cards with score and a "jump to it" action, and a verified indicator.
import { useState, type FormEvent } from "react";
import { Icon } from "./icons";
import { Badge, btnPrimary, card, inputPill, type Tone } from "./ui";
import type { AnswerCitation, AnswerResponse } from "@/lib/video";

const STATUS_LABEL: Record<AnswerResponse["status"], [string, Tone]> = {
  repondu: ["Answer found", "green"],
  confiance_faible: ["Low confidence: check the passages", "orange"],
  hors_sujet: ["Not in the sources", "gray"],
};

type Turn = { question: string; answer?: AnswerResponse; error?: string; busy: boolean };

export function AssistantPanel({
  emptyIcon = "chat",
  emptyTitle,
  emptyText,
  placeholder = "Ask a question…",
  disabled = false,
  disabledHint,
  busyText = "Searching the sources and checking the answer… (can take up to 20 s)",
  documentId = "",
  onAsk,
  onJump,
}: {
  emptyIcon?: Parameters<typeof Icon>[0]["name"];
  emptyTitle: string;
  emptyText: string;
  placeholder?: string;
  disabled?: boolean;
  disabledHint?: string;
  busyText?: string;
  // Source the current question/answer belongs to: needed so "Jump to it" on a passage (which
  // has no document_id of its own) can still navigate back to the right source.
  documentId?: string;
  onAsk: (question: string) => Promise<AnswerResponse>;
  onJump?: (citation: AnswerCitation) => void;
}) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || disabled) return;
    setQuestion("");
    setTurns((t) => [...t, { question: q, busy: true }]);
    try {
      const answer = await onAsk(q);
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, answer, busy: false } : turn)));
    } catch (err) {
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, error: (err as Error).message, busy: false } : turn)));
    }
  }

  return (
    <div className={`${card} flex flex-col p-6`}>
      {turns.length === 0 ? (
        <div className="flex flex-col items-center px-2 py-10 text-center">
          <span className="inline-flex size-12 items-center justify-center rounded-full bg-primary-50 text-primary-500 dark:bg-primary-500/15">
            <Icon name={emptyIcon} className="size-6" />
          </span>
          <p className="mt-4 font-semibold text-gray-800 dark:text-white/90">{emptyTitle}</p>
          <p className="mt-1 max-w-sm text-sm text-gray-500 dark:text-gray-400">{emptyText}</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {turns.map((turn, i) => (
            <AnswerTurn key={i} turn={turn} busyText={busyText} documentId={documentId} onJump={onJump} />
          ))}
        </div>
      )}

      <form onSubmit={submit} className={`flex gap-2 ${turns.length > 0 ? "mt-6" : ""}`}>
        <input
          className={inputPill}
          value={question}
          maxLength={1000}
          disabled={disabled}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={disabled ? disabledHint ?? placeholder : placeholder}
          aria-label="Question"
        />
        <button type="submit" disabled={disabled || !question.trim()} className={`${btnPrimary} h-12 shrink-0 disabled:opacity-50`}>
          <Icon name="chat" className="size-4" />
        </button>
      </form>
    </div>
  );
}

function AnswerTurn({
  turn,
  busyText,
  documentId,
  onJump,
}: {
  turn: Turn;
  busyText: string;
  documentId: string;
  onJump?: (citation: AnswerCitation) => void;
}) {
  return (
    <div>
      <div className="flex items-start gap-2">
        <span className="mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-500 dark:bg-white/10 dark:text-gray-400">
          <Icon name="chat" className="size-3.5" />
        </span>
        <p className="rounded-2xl bg-gray-50 px-4 py-2.5 text-sm text-gray-800 dark:bg-white/5 dark:text-white/90">{turn.question}</p>
      </div>

      <div className="mt-3 pl-8">
        {turn.busy && (
          <p className="inline-flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <Icon name="refresh" className="size-3.5 animate-spin" />
            {busyText}
          </p>
        )}
        {turn.error && <p className="text-sm text-error-500">{turn.error}</p>}
        {turn.answer && <AnswerBody answer={turn.answer} documentId={documentId} onJump={onJump} />}
      </div>
    </div>
  );
}

function AnswerBody({
  answer,
  documentId,
  onJump,
}: {
  answer: AnswerResponse;
  documentId: string;
  onJump?: (citation: AnswerCitation) => void;
}) {
  const [label, tone] = STATUS_LABEL[answer.status];
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={tone}>{label}</Badge>
        {answer.verifie && (
          <span
            className="inline-flex items-center gap-1 text-xs font-medium text-success-600 dark:text-[#6CE9A6]"
            title="The answer is grounded in a retrieved passage — this does not confirm the passage is the correct one."
          >
            <Icon name="shield" className="size-3.5" />
            Grounded in a source
          </span>
        )}
      </div>

      <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-gray-800 dark:text-white/90">{answer.reponse}</p>

      {answer.citations.length > 0 && (
        <div className="mt-3 space-y-2">
          {answer.citations.map((c, i) => (
            <CitationCard key={i} citation={c} onJump={onJump} />
          ))}
        </div>
      )}

      {answer.passages.length > 0 && (
        <details className="mt-4" open={answer.status !== "repondu"}>
          <summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">
            Passages used ({answer.passages.length})
          </summary>
          <ol className="mt-3 space-y-3">
            {answer.passages.map((p) => (
              <li key={p.chunk_id} className="rounded-xl bg-gray-50 p-3 text-sm dark:bg-white/5">
                <div className="mb-1 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span className="font-medium">{p.timestamp}</span>
                  <div className="flex items-center gap-2">
                    <span title="Reranker relevance score">score {p.rerank.toFixed(3)}</span>
                    {onJump && (
                      <button
                        type="button"
                        onClick={() => onJump({ chunk_id: p.chunk_id, document_id: documentId, source: "", text: p.text, timestamp: p.timestamp, url: null })}
                        className="font-medium text-primary-600 hover:underline dark:text-primary-300"
                      >
                        Jump to it
                      </button>
                    )}
                  </div>
                </div>
                <p className="line-clamp-4 text-gray-700 dark:text-gray-300">{p.text}</p>
              </li>
            ))}
          </ol>
        </details>
      )}

      {Object.keys(answer.timings).length > 0 && (
        <p className="mt-3 text-xs text-gray-400">
          {Object.entries(answer.timings)
            .map(([k, v]) => `${k} ${v.toFixed(1)} s`)
            .join(" · ")}
        </p>
      )}
    </div>
  );
}

function CitationCard({ citation, onJump }: { citation: AnswerCitation; onJump?: (citation: AnswerCitation) => void }) {
  const clickable = Boolean(onJump && citation.timestamp) || Boolean(citation.url);
  const body = (
    <blockquote className="border-l-4 border-primary-400 pl-4">
      <p className="text-sm leading-relaxed text-gray-800 dark:text-white/90">« {citation.text} »</p>
      <p className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-primary-600 dark:text-primary-300">
        {citation.timestamp ? (
          <>
            <Icon name="clock" className="size-3.5" />
            {citation.timestamp}
          </>
        ) : (
          <>
            <Icon name="web" className="size-3.5" />
            {citation.source}
          </>
        )}
        {clickable && <span className="text-gray-400">· {citation.timestamp ? "jump to it" : "open the paper"}</span>}
      </p>
    </blockquote>
  );

  if (onJump && (citation.timestamp || citation.url)) {
    return (
      <button type="button" onClick={() => onJump(citation)} className="block w-full text-left transition hover:opacity-80">
        {body}
      </button>
    );
  }
  if (citation.url) {
    return (
      <a href={citation.url} target="_blank" rel="noreferrer" className="block transition hover:opacity-80">
        {body}
      </a>
    );
  }
  return body;
}
