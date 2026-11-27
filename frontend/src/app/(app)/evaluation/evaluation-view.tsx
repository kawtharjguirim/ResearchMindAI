"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";
import { Badge, btnPrimary, btnSecondary, card, inputPill } from "@/components/ui";
import { EVAL_STATUS, evaluationApi, type EvalQuestion, type EvalStatus } from "@/lib/evaluation";
import { domainLabel, domainTone } from "@/lib/papers";

type Filter = EvalStatus | "all";

const textarea =
  "w-full rounded-2xl border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 shadow-theme-xs focus:border-primary-300 focus:outline-0 focus:ring-3 focus:ring-primary-300/20 dark:border-gray-700 dark:text-white/90";
const label = "mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300";

function Reviewer({
  q,
  onSave,
  onPrev,
  onNext,
}: {
  q: EvalQuestion;
  onSave: (body: { statut: EvalStatus; question: string; reference: string; commentaire: string }) => Promise<void>;
  onPrev?: () => void;
  onNext?: () => void;
}) {
  const [question, setQuestion] = useState(q.question);
  const [reference, setReference] = useState(q.reference);
  const [commentaire, setCommentaire] = useState(q.commentaire);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setQuestion(q.question);
    setReference(q.reference);
    setCommentaire(q.commentaire);
  }, [q]);

  const edited = question.trim() !== q.question_initiale || reference.trim() !== q.reference_initiale;
  const [statusText, statusTone] = EVAL_STATUS[q.statut];

  async function save(statut: EvalStatus) {
    setBusy(true);
    try {
      await onSave({ statut, question, reference, commentaire });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`${card} p-6`}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={statusTone}>{statusText}</Badge>
        <Badge tone={domainTone(q.domaine)}>{domainLabel(q.domaine)}</Badge>
        <Badge tone="gray">{q.split}</Badge>
        <span className="text-xs text-gray-400">{q.id}</span>
        <div className="ml-auto flex gap-1">
          <button type="button" onClick={onPrev} disabled={!onPrev} className="rounded-full p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-30 dark:hover:bg-white/10" aria-label="Previous question">
            <Icon name="arrowLeft" className="size-4" />
          </button>
          <button type="button" onClick={onNext} disabled={!onNext} className="rounded-full p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-30 dark:hover:bg-white/10" aria-label="Next question">
            <Icon name="arrowLeft" className="size-4 rotate-180" />
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-gray-800 dark:text-white/90">{q.titre}</p>
        <Link href={`/papers/${encodeURIComponent(q.document_id)}?chunk=${encodeURIComponent(q.chunk_id)}`} target="_blank" className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:underline dark:text-primary-300">
          <Icon name="pdf" className="size-3.5" />
          Open the paper
        </Link>
      </div>
      <blockquote className="mt-2 max-h-72 overflow-y-auto rounded-xl border-l-4 border-primary-400 bg-gray-50 p-4 text-sm leading-relaxed text-gray-700 dark:bg-white/5 dark:text-gray-300">
        {q.section && <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-primary-600 dark:text-primary-300">{q.section}</p>}
        {q.passage}
      </blockquote>

      <div className="mt-5 space-y-4">
        <div>
          <label htmlFor="eval-question" className={label}>
            Question <span className="font-normal text-gray-400">(must be answerable from this passage alone)</span>
          </label>
          <textarea id="eval-question" rows={2} className={textarea} value={question} onChange={(e) => setQuestion(e.target.value)} />
        </div>
        <div>
          <label htmlFor="eval-reference" className={label}>
            Reference answer <span className="font-normal text-gray-400">(faithful to the passage)</span>
          </label>
          <textarea id="eval-reference" rows={3} className={textarea} value={reference} onChange={(e) => setReference(e.target.value)} />
        </div>
        <div>
          <label htmlFor="eval-comment" className={label}>
            Comment <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <input id="eval-comment" className={inputPill} value={commentaire} maxLength={1000} onChange={(e) => setCommentaire(e.target.value)} placeholder="Why it was corrected or rejected" />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button type="button" disabled={busy || question.trim().length < 5 || !reference.trim()} onClick={() => save(edited ? "corrige" : "valide")} className={`${btnPrimary} disabled:opacity-50`}>
          <Icon name="check" className="size-4" />
          {edited ? "Save correction" : "Validate"}
        </button>
        <button type="button" disabled={busy} onClick={() => save("rejete")} className={`${btnSecondary} hover:text-error-500`}>
          <Icon name="x" className="size-4" />
          Reject
        </button>
        {edited && (
          <button
            type="button"
            onClick={() => {
              setQuestion(q.question_initiale);
              setReference(q.reference_initiale);
            }}
            className="text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400"
          >
            Reset to original
          </button>
        )}
      </div>
    </div>
  );
}

export function EvaluationView() {
  const toast = useToast();
  const [items, setItems] = useState<EvalQuestion[] | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("a_valider");
  const [domain, setDomain] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError("");
    try {
      setItems(await evaluationApi.list());
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const c: Record<EvalStatus, number> = { a_valider: 0, valide: 0, corrige: 0, rejete: 0 };
    for (const q of items ?? []) c[q.statut]++;
    return c;
  }, [items]);

  const shown = useMemo(
    () => (items ?? []).filter((q) => (filter === "all" || q.statut === filter) && (!domain || q.domaine === domain)),
    [items, filter, domain],
  );

  const selected = items?.find((q) => q.id === selectedId) ?? shown[0] ?? null;
  const pos = selected ? shown.findIndex((q) => q.id === selected.id) : -1;
  const domains = useMemo(() => [...new Set((items ?? []).map((q) => q.domaine))].sort(), [items]);

  async function save(q: EvalQuestion, body: { statut: EvalStatus; question: string; reference: string; commentaire: string }) {
    try {
      const updated = await evaluationApi.update(q.id, body);
      const next = shown.slice(pos + 1).find((x) => x.statut === "a_valider" && x.id !== q.id) ?? shown[pos + 1] ?? null;
      setItems((list) => list?.map((x) => (x.id === q.id ? updated : x)) ?? null);
      setSelectedId(next?.id ?? updated.id);
      toast(`${q.id}: ${EVAL_STATUS[updated.statut][0].toLowerCase()}`);
    } catch (err) {
      toast((err as Error).message, false);
    }
  }

  const total = items?.length ?? 0;
  const reviewed = total - counts.a_valider;
  const chip = (active: boolean) =>
    `inline-flex h-9 items-center gap-1.5 rounded-full px-4 text-sm font-medium transition ${
      active
        ? "bg-primary-500 text-white shadow-theme-xs"
        : "border border-gray-200 bg-white text-gray-600 hover:border-primary-300 hover:text-primary-600 dark:border-gray-700 dark:bg-white/5 dark:text-gray-300"
    }`;

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Evaluation set</h1>
      <p className="mt-1 max-w-3xl text-sm text-gray-500 dark:text-gray-400">
        Questions on the arXiv corpus, one per passage, written by Claude. Validate, correct or reject each one: only reviewed
        questions count when the search engine is evaluated (<code className="text-xs">rag/evaluation_corpus.py</code>).
      </p>

      {error ? (
        <div className={`${card} mt-6 p-6 text-sm`}>
          <p className="text-error-500">{error}</p>
          <button type="button" onClick={load} className={`${btnSecondary} mt-3`}>
            Try again
          </button>
        </div>
      ) : items === null ? (
        <div className={`${card} mt-6 h-64 animate-pulse`} />
      ) : (
        <>
          <div className={`${card} mt-6 p-5`}>
            <div className="flex items-baseline justify-between text-sm">
              <span className="font-medium text-gray-800 dark:text-white/90">
                {reviewed} / {total} reviewed
              </span>
              <span className="text-gray-500 dark:text-gray-400">
                {counts.valide} validated · {counts.corrige} corrected · {counts.rejete} rejected
              </span>
            </div>
            <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
              <div className="bg-success-600" style={{ width: `${(100 * counts.valide) / Math.max(total, 1)}%` }} />
              <div className="bg-[#4E6EFF]" style={{ width: `${(100 * counts.corrige) / Math.max(total, 1)}%` }} />
              <div className="bg-error-500" style={{ width: `${(100 * counts.rejete) / Math.max(total, 1)}%` }} />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {(["a_valider", "valide", "corrige", "rejete"] as EvalStatus[]).map((s) => (
              <button key={s} type="button" className={chip(filter === s)} onClick={() => setFilter(s)}>
                {EVAL_STATUS[s][0]} <span className="opacity-70">{counts[s]}</span>
              </button>
            ))}
            <button type="button" className={chip(filter === "all")} onClick={() => setFilter("all")}>
              All <span className="opacity-70">{total}</span>
            </button>
            <select className={`${inputPill} h-9 w-auto py-0 text-sm`} value={domain} onChange={(e) => setDomain(e.target.value)} aria-label="Domain">
              <option value="">All domains</option>
              {domains.map((d) => (
                <option key={d} value={d}>
                  {domainLabel(d)}
                </option>
              ))}
            </select>
          </div>

          {shown.length === 0 ? (
            <div className={`${card} mt-6 flex flex-col items-center px-6 py-14 text-center`}>
              <span className="inline-flex size-12 items-center justify-center rounded-full bg-success-50 text-success-600 dark:bg-success-600/15">
                <Icon name="check" className="size-6" />
              </span>
              <p className="mt-4 font-semibold text-gray-800 dark:text-white/90">Nothing left in this filter</p>
            </div>
          ) : (
            <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
              <ol className={`${card} max-h-[75vh] overflow-y-auto p-2`}>
                {shown.map((q) => {
                  const [, tone] = EVAL_STATUS[q.statut];
                  const active = selected?.id === q.id;
                  return (
                    <li key={q.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(q.id)}
                        className={`flex w-full items-start gap-2.5 rounded-xl px-3 py-2.5 text-left transition ${active ? "bg-primary-50 dark:bg-primary-500/10" : "hover:bg-gray-50 dark:hover:bg-white/5"}`}
                      >
                        <span
                          className={`mt-1.5 size-2 shrink-0 rounded-full ${tone === "green" ? "bg-success-600" : tone === "blue" ? "bg-[#4E6EFF]" : tone === "red" ? "bg-error-500" : "bg-gray-300 dark:bg-gray-600"}`}
                        />
                        <span className="min-w-0">
                          <span className="block text-xs text-gray-400">{q.id}</span>
                          <span className="line-clamp-2 text-sm text-gray-700 dark:text-gray-300">{q.question}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>
              {selected && (
                <Reviewer
                  q={selected}
                  onSave={(body) => save(selected, body)}
                  onPrev={pos > 0 ? () => setSelectedId(shown[pos - 1].id) : undefined}
                  onNext={pos >= 0 && pos < shown.length - 1 ? () => setSelectedId(shown[pos + 1].id) : undefined}
                />
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
