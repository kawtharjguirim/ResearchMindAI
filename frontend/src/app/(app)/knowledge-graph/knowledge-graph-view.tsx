"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";
import { Badge, btnPrimary, btnSecondary, card, inputPill, Progress, type Tone } from "@/components/ui";
import {
  documentHref,
  ENTITY_TYPES,
  knowledgeApi,
  type EntityType,
  type GraphEdge,
  type GraphStats,
  type GraphView,
  type Job,
  type Proposal,
  type Verification,
} from "@/lib/knowledge";
import { videoApi, type Source } from "@/lib/video";

const POLL_MS = 3000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

const TYPE_TONE: Record<EntityType, Tone> = { Method: "violet", Dataset: "blue", Result: "green", Concept: "orange" };
const TYPE_COLOR: Record<EntityType | "Document", string> = {
  Document: "#667085",
  Method: "#7A5AF8",
  Dataset: "#4E6EFF",
  Result: "#12B76A",
  Concept: "#F79009",
};
const VERIFICATION: Record<Verification, [string, Tone]> = {
  VERIFIED: ["Verified", "green"],
  NEEDS_REVIEW: ["Needs review", "orange"],
  REJECTED: ["Rejected", "red"],
};

// Nombre lu dans le résumé de la tâche (ex. « 4 déjà connues »), ou null s'il n'y figure pas.
function compte(message: string | undefined, motif: RegExp): number | null {
  const m = message ? motif.exec(message) : null;
  return m ? Number(m[1]) : null;
}

function SourceLink({ documentKey, title, location }: { documentKey: string; title: string; location?: string }) {
  const lien = documentHref(documentKey);
  const texte = `${title}${location ? ` · ${location}` : ""}`;
  if (!lien) return <span>{texte}</span>;
  return lien.external ? (
    <a href={lien.href} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline dark:text-primary-300">
      {texte}
    </a>
  ) : (
    <Link href={lien.href} className="text-primary-600 hover:underline dark:text-primary-300">
      {texte}
    </Link>
  );
}

// ---------- Statistiques ----------

function StatsRow({ stats, error }: { stats: GraphStats | null; error: string }) {
  if (error) {
    return (
      <div className={`${card} mt-6 flex items-start gap-3 p-5 text-sm`}>
        <Icon name="alert" className="mt-0.5 size-4 shrink-0 text-error-500" />
        <div>
          <p className="font-medium text-gray-800 dark:text-white/90">The graph database is unavailable</p>
          <p className="mt-1 text-gray-500 dark:text-gray-400">{error} Start it with « docker compose up -d neo4j ».</p>
        </div>
      </div>
    );
  }
  const items: [string, number | undefined][] = [
    ["Corpus articles", stats?.noeuds.Paper],
    ["References", stats?.noeuds.Reference],
    ["Authors", stats?.noeuds.Author],
    ["Citations", stats?.relations.CITES],
    ["Your entities", ENTITY_TYPES.reduce((s, t) => s + (stats?.noeuds[t] ?? 0), 0)],
  ];
  return (
    <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {items.map(([label, value]) => (
        <div key={label} className={`${card} p-4`}>
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
          <p className="mt-1 text-xl font-semibold text-gray-800 dark:text-white/90">{stats ? (value ?? 0).toLocaleString("en-GB") : "—"}</p>
        </div>
      ))}
    </div>
  );
}

// ---------- Agents ----------

function AgentCard({ title, icon, state, tone, children }: { title: string; icon: Parameters<typeof Icon>[0]["name"]; state: string; tone: Tone; children: React.ReactNode }) {
  return (
    <div className={`${card} p-5`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon name={icon} className="size-4 text-primary-500" />
          <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">{title}</h3>
        </div>
        <Badge tone={tone}>{state}</Badge>
      </div>
      <div className="mt-3 space-y-1.5 text-xs text-gray-600 dark:text-gray-300">{children}</div>
    </div>
  );
}

function AgentsPanel({ job, pending, onStart }: { job: Job | null; pending: Proposal[]; onStart: (job: Job) => void }) {
  const toast = useToast();
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [corpusLimit, setCorpusLimit] = useState(1);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    videoApi
      .listSources()
      .then((list) => setSources(list.filter((s) => s.status === "ready" && UUID.test(s.id))))
      .catch(() => setSources([]));
  }, []);

  const running = job?.status === "queued" || job?.status === "running";
  const [docState, docTone]: [string, Tone] = !job ? ["Idle", "gray"] : running ? ["Processing", "blue"] : job.status === "done" ? ["Completed", "green"] : ["Failed", "red"];
  const parType = ENTITY_TYPES.map((t) => [t, pending.filter((p) => p.entity_type === t).length] as const);
  const verified = pending.filter((p) => p.verification_status === "VERIFIED").length;
  const review = pending.filter((p) => p.verification_status === "NEEDS_REVIEW").length;

  async function start(lancer: () => Promise<Job>) {
    setBusy(true);
    try {
      onStart(await lancer());
      toast("Extraction started");
    } catch (err) {
      toast((err as Error).message, false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-8">
      <h2 className="text-base font-semibold text-gray-800 dark:text-white/90">AI Knowledge Agents</h2>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        Entities are extracted from your documents with their exact sentence. Nothing enters the graph until you approve it.
      </p>

      <div className={`${card} mt-4 grid gap-4 p-5 lg:grid-cols-2`}>
        <div>
          <label htmlFor="kg-source" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Extract from one of your sources
          </label>
          <div className="flex gap-2">
            <select id="kg-source" className={inputPill} value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
              <option value="">Choose a ready source</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
            <button type="button" disabled={!sourceId || busy || running} onClick={() => start(() => knowledgeApi.extractSource(sourceId))} className={`${btnPrimary} shrink-0 disabled:opacity-50`}>
              Extract
            </button>
          </div>
        </div>
        <div>
          <label htmlFor="kg-corpus" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Extract from corpus articles (several minutes each)
          </label>
          <div className="flex gap-2">
            <input id="kg-corpus" type="number" min={1} max={80} className={inputPill} value={corpusLimit} onChange={(e) => setCorpusLimit(Math.min(80, Math.max(1, Number(e.target.value) || 1)))} />
            <button type="button" disabled={busy || running} onClick={() => start(() => knowledgeApi.extractCorpus(corpusLimit))} className={`${btnSecondary} shrink-0 disabled:opacity-50`}>
              Extract
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <AgentCard title="Document Agent" icon="pdf" state={docState} tone={docTone}>
          {job ? (
            <>
              <p>{job.kind === "corpus" ? `Corpus: ${job.target}` : "One source"}</p>
              {job.total > 0 && <Progress value={Math.round((100 * job.progress) / job.total)} />}
              <p>
                {job.progress} / {job.total} {job.kind === "corpus" ? "articles" : "passages"}
              </p>
              {job.message && <p className="text-gray-500 dark:text-gray-400">{job.message}</p>}
            </>
          ) : (
            <p>Start an extraction to read a document.</p>
          )}
        </AgentCard>
        <AgentCard title="Knowledge Agent" icon="network" state={`${pending.length} pending`} tone="violet">
          {parType.map(([t, n]) => (
            <p key={t} className="flex justify-between">
              <span>{t}</span>
              <span className="font-medium">{n}</span>
            </p>
          ))}
          {compte(job?.message, /(\d+) déjà connues/) !== null && <p>Duplicates skipped: {compte(job?.message, /(\d+) déjà connues/)}</p>}
        </AgentCard>
        <AgentCard title="Verification Agent" icon="shield" state={review ? `${review} to review` : "Up to date"} tone={review ? "orange" : "green"}>
          <p className="flex justify-between">
            <span>Verified (sentence found in the passage)</span>
            <span className="font-medium">{verified}</span>
          </p>
          <p className="flex justify-between">
            <span>Needs review</span>
            <span className="font-medium">{review}</span>
          </p>
          {compte(job?.message, /(\d+) rejetées/) !== null && (
            <p className="flex justify-between">
              <span>Rejected in the last run</span>
              <span className="font-medium">{compte(job?.message, /(\d+) rejetées/)}</span>
            </p>
          )}
        </AgentCard>
      </div>
    </section>
  );
}

// ---------- Validation ----------

function ProposalCard({ p, onDecide }: { p: Proposal; onDecide?: (p: Proposal, decision: "approve" | "reject") => Promise<void> }) {
  const [busy, setBusy] = useState<"" | "approve" | "reject">("");
  const [vText, vTone] = VERIFICATION[p.verification_status];
  async function decide(d: "approve" | "reject") {
    if (!onDecide) return;
    setBusy(d);
    try {
      await onDecide(p, d);
    } finally {
      setBusy("");
    }
  }
  return (
    <li className="rounded-2xl border border-gray-100 p-4 dark:border-white/5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={TYPE_TONE[p.entity_type]}>{p.entity_type}</Badge>
        <span className="text-sm font-medium text-gray-800 dark:text-white/90">{p.name}</span>
        <Badge tone={vTone}>{vText}</Badge>
        {p.status !== "pending" && <Badge tone={p.status === "approved" ? "green" : "gray"}>{p.status === "approved" ? "Approved" : "Rejected"}</Badge>}
      </div>
      <blockquote className="mt-2 border-l-2 border-primary-200 pl-3 text-sm text-gray-600 dark:border-primary-500/40 dark:text-gray-300">« {p.excerpt} »</blockquote>
      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        Source: <SourceLink documentKey={p.document_key} title={p.document_title} location={p.location} />
      </p>
      {onDecide && (
        <div className="mt-3 flex gap-2">
          <button type="button" disabled={!!busy} onClick={() => decide("approve")} className={`${btnPrimary} h-9 px-4 disabled:opacity-50`}>
            <Icon name={busy === "approve" ? "refresh" : "check"} className={`size-4 ${busy === "approve" ? "animate-spin" : ""}`} />
            Approve
          </button>
          <button type="button" disabled={!!busy} onClick={() => decide("reject")} className={`${btnSecondary} h-9 px-4 disabled:opacity-50`}>
            <Icon name="x" className="size-4" />
            Reject
          </button>
        </div>
      )}
    </li>
  );
}

function ReviewList({ pending, onDecide }: { pending: Proposal[] | null; onDecide: (p: Proposal, d: "approve" | "reject") => Promise<void> }) {
  const [type, setType] = useState<EntityType | "all">("all");
  const [verif, setVerif] = useState<Verification | "all">("all");
  if (pending === null) return <div className="mt-4 h-24 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />;
  const visibles = pending.filter((p) => (type === "all" || p.entity_type === type) && (verif === "all" || p.verification_status === verif));
  return (
    <div>
      <div className="mt-4 flex flex-wrap gap-2">
        {(["all", ...ENTITY_TYPES] as const).map((t) => (
          <button key={t} type="button" onClick={() => setType(t)} className={`rounded-full px-3 py-1 text-xs transition ${type === t ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900" : "border border-gray-200 text-gray-600 dark:border-white/10 dark:text-gray-300"}`}>
            {t === "all" ? "All types" : t}
          </button>
        ))}
        <span className="mx-1 w-px bg-gray-200 dark:bg-white/10" />
        {(["all", "VERIFIED", "NEEDS_REVIEW"] as const).map((v) => (
          <button key={v} type="button" onClick={() => setVerif(v)} className={`rounded-full px-3 py-1 text-xs transition ${verif === v ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900" : "border border-gray-200 text-gray-600 dark:border-white/10 dark:text-gray-300"}`}>
            {v === "all" ? "Any status" : VERIFICATION[v][0]}
          </button>
        ))}
      </div>
      {visibles.length === 0 ? (
        <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
          {pending.length === 0 ? "No proposal waiting for review. Start an extraction above." : "No proposal matches these filters."}
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {visibles.map((p) => (
            <ProposalCard key={p.id} p={p} onDecide={onDecide} />
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------- Graphe ----------

function GraphPanel({ view, error }: { view: GraphView | null; error: string }) {
  const [types, setTypes] = useState<EntityType[]>([...ENTITY_TYPES]);
  const [selected, setSelected] = useState<string | null>(null);

  const { docs, entities, edges } = useMemo(() => {
    const visibles = (view?.nodes ?? []).filter((n) => n.type === "Document" || types.includes(n.type as EntityType));
    const ids = new Set(visibles.map((n) => n.id));
    const liens = (view?.edges ?? []).filter((e) => ids.has(e.source) && ids.has(e.target));
    const relies = new Set(liens.flatMap((e) => [e.source, e.target]));
    return {
      docs: visibles.filter((n) => n.type === "Document" && relies.has(n.id)),
      entities: visibles.filter((n) => n.type !== "Document").sort((a, b) => a.type.localeCompare(b.type) || a.label.localeCompare(b.label)),
      edges: liens,
    };
  }, [view, types]);

  if (error) return <p className="mt-6 text-sm text-error-500">{error}</p>;
  if (view === null) return <div className="mt-4 h-64 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />;
  if (view.nodes.length === 0) return <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">The graph is empty: approve proposals to add entities and their sources.</p>;

  const ROW = 30;
  const height = Math.max(docs.length, entities.length) * ROW + 40;
  const pos = new Map<string, { x: number; y: number }>();
  docs.forEach((n, i) => pos.set(n.id, { x: 200, y: 30 + i * ROW + (entities.length > docs.length ? ((entities.length - docs.length) * ROW) / 2 : 0) }));
  entities.forEach((n, i) => pos.set(n.id, { x: 560, y: 30 + i * ROW }));
  const label = (s: string) => (s.length > 32 ? `${s.slice(0, 31)}…` : s);
  const detail: GraphEdge[] = selected ? edges.filter((e) => e.source === selected || e.target === selected) : [];
  const nom = (id: string) => view.nodes.find((n) => n.id === id)?.label ?? id;

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
      <div className={`${card} overflow-auto p-4`}>
        <div className="mb-3 flex flex-wrap gap-2">
          {ENTITY_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTypes((l) => (l.includes(t) ? l.filter((x) => x !== t) : [...l, t]))}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition ${types.includes(t) ? "border-gray-300 text-gray-800 dark:border-white/20 dark:text-white/90" : "border-gray-100 text-gray-400 line-through dark:border-white/5"}`}
            >
              <span className="size-2 rounded-full" style={{ background: TYPE_COLOR[t] }} />
              {t}
            </button>
          ))}
        </div>
        <svg width="780" height={height} role="img" aria-label="Validated knowledge graph">
          {edges.map((e, i) => {
            const a = pos.get(e.source)!;
            const b = pos.get(e.target)!;
            const actif = selected === e.source || selected === e.target;
            return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={actif ? "#7A5AF8" : "#D0D5DD"} strokeWidth={actif ? 1.8 : 1} />;
          })}
          {[...docs, ...entities].map((n) => {
            const p = pos.get(n.id)!;
            const doc = n.type === "Document";
            return (
              <g key={n.id} onClick={() => setSelected(n.id === selected ? null : n.id)} className="cursor-pointer">
                <circle cx={p.x} cy={p.y} r={selected === n.id ? 8 : 6} fill={TYPE_COLOR[n.type]} />
                <text x={doc ? p.x - 12 : p.x + 12} y={p.y + 4} textAnchor={doc ? "end" : "start"} fontSize="12" className="fill-gray-700 dark:fill-gray-300">
                  {label(n.label)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className={`${card} p-5`}>
        {selected ? (
          <>
            <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">{nom(selected)}</h3>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{detail.length} relation(s), each with its evidence</p>
            <ul className="mt-3 space-y-3">
              {detail.map((e, i) => (
                <li key={i} className="text-sm">
                  <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                    {nom(e.source)} — {e.relation} → {nom(e.target)}
                  </p>
                  <blockquote className="mt-1 border-l-2 border-primary-200 pl-3 text-gray-600 dark:border-primary-500/40 dark:text-gray-300">« {e.phrase} »</blockquote>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    <SourceLink documentKey={e.document_key} title={nom(e.source)} location={e.location} />
                  </p>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">Click a document or an entity to see its relations and the sentences that support them.</p>
        )}
      </div>
    </div>
  );
}

// ---------- Page ----------

type Tab = "review" | "graph" | "history";

export function KnowledgeGraphView() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("review");
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [statsError, setStatsError] = useState("");
  const [view, setView] = useState<GraphView | null>(null);
  const [viewError, setViewError] = useState("");
  const [pending, setPending] = useState<Proposal[] | null>(null);
  const [history, setHistory] = useState<Proposal[] | null>(null);
  const [job, setJob] = useState<Job | null>(null);

  const loadGraph = useCallback(async () => {
    try {
      setStats(await knowledgeApi.stats());
      setStatsError("");
    } catch (err) {
      setStatsError((err as Error).message);
    }
    try {
      setView(await knowledgeApi.view());
      setViewError("");
    } catch (err) {
      setViewError((err as Error).message);
    }
  }, []);

  const loadProposals = useCallback(async () => {
    try {
      const [p, h] = await Promise.all([knowledgeApi.proposals("pending"), knowledgeApi.history()]);
      setPending(p);
      setHistory(h);
    } catch (err) {
      toast((err as Error).message, false);
      setPending([]);
      setHistory([]);
    }
  }, [toast]);

  useEffect(() => {
    loadGraph();
    loadProposals();
  }, [loadGraph, loadProposals]);

  // Suivi de la tâche en cours : progression, puis rechargement des propositions à la fin.
  const running = job?.status === "queued" || job?.status === "running";
  useEffect(() => {
    if (!job || !running) return;
    const t = setInterval(async () => {
      try {
        const j = await knowledgeApi.job(job.id);
        setJob(j);
        if (j.status === "done" || j.status === "failed") loadProposals();
      } catch {
        // Erreur réseau passagère : nouvel essai au prochain intervalle.
      }
    }, POLL_MS);
    return () => clearInterval(t);
  }, [job, running, loadProposals]);

  async function decide(p: Proposal, d: "approve" | "reject") {
    try {
      const updated = d === "approve" ? await knowledgeApi.approve(p.id) : await knowledgeApi.reject(p.id);
      setPending((l) => l?.filter((x) => x.id !== p.id) ?? null);
      setHistory((l) => [updated, ...(l ?? [])]);
      toast(d === "approve" ? `${p.name} added to the graph` : `${p.name} rejected`);
      if (d === "approve") loadGraph();
    } catch (err) {
      toast((err as Error).message, false);
    }
  }

  const tabs: [Tab, string][] = [
    ["review", `Review${pending ? ` (${pending.length})` : ""}`],
    ["graph", "Graph"],
    ["history", "History"],
  ];

  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">Knowledge Graph</h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Articles, references and authors from the corpus, plus the methods, datasets, results and concepts you approved.</p>

      <StatsRow stats={stats} error={statsError} />
      <AgentsPanel job={job} pending={pending ?? []} onStart={setJob} />

      <section className="mt-8">
        <div className="flex gap-2 border-b border-gray-100 dark:border-white/5">
          {tabs.map(([id, text]) => (
            <button key={id} type="button" onClick={() => setTab(id)} className={`-mb-px border-b-2 px-3 py-2 text-sm transition ${tab === id ? "border-primary-500 font-medium text-gray-800 dark:text-white/90" : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"}`}>
              {text}
            </button>
          ))}
        </div>
        {tab === "review" && <ReviewList pending={pending} onDecide={decide} />}
        {tab === "graph" && <GraphPanel view={view} error={viewError} />}
        {tab === "history" &&
          (history === null ? (
            <div className="mt-4 h-24 animate-pulse rounded-2xl bg-gray-100 dark:bg-white/10" />
          ) : history.length === 0 ? (
            <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">No decision yet.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {history.map((p) => (
                <ProposalCard key={p.id} p={p} />
              ))}
            </ul>
          ))}
      </section>
    </div>
  );
}
