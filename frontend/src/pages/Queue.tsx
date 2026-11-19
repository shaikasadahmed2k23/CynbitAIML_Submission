import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Copy, Inbox, Search, X } from "lucide-react";
import { api } from "../lib/api";
import type { QueueItem, ReviewResponse, Stats, Triage } from "../lib/types";
import ReviewResult from "../components/ReviewResult";
import { EmptyState, ErrorCard, Skeleton, StatTile, TriageBadge } from "../components/ui";

type SortKey = "priority" | "score" | "intern" | "track";
const FILTERS: { v: Triage | "ALL"; label: string }[] = [
  { v: "ALL", label: "All" }, { v: "BLOCKER", label: "Blockers" }, { v: "NEEDS_MENTOR", label: "Needs mentor" }, { v: "AUTO_APPROVE", label: "Auto-approve" },
];

function Drawer({ id, onClose }: { id: string; onClose: () => void }) {
  const [r, setR] = useState<ReviewResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    api.getReview(id).then(setR).catch((e) => setErr(e.message));
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [id, onClose]);
  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label="Review details">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={onClose} />
      <aside className="slidein absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto bg-page p-4 shadow-lift sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <p className="label">Full review</p>
          <button ref={closeRef} onClick={onClose} aria-label="Close" className="rounded-full border border-line bg-white p-2 text-ink hover:bg-cardAlt"><X className="h-4 w-4" /></button>
        </div>
        {err ? <ErrorCard message={err} /> : !r ? <div className="space-y-4"><Skeleton className="h-48" /><Skeleton className="h-64" /></div> : <ReviewResult r={r} />}
      </aside>
    </div>
  );
}

export default function Queue() {
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Triage | "ALL">("ALL");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<{ k: SortKey; dir: 1 | -1 }>({ k: "priority", dir: -1 });
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    Promise.all([api.queue(), api.stats()]).then(([i, s]) => { setItems(i); setStats(s); }).catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  const rows = useMemo(() => {
    const term = q.trim().toLowerCase();
    return (items ?? [])
      .filter((i) => (filter === "ALL" || i.triage === filter) && (!term || `${i.id} ${i.intern} ${i.track} ${i.title}`.toLowerCase().includes(term)))
      .sort((a, b) => {
        const av = a[sort.k], bv = b[sort.k];
        return (typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number)) * sort.dir;
      });
  }, [items, filter, q, sort]);

  const th = (k: SortKey, label: string, cls = "") => (
    <th scope="col" className={`px-4 py-3 text-left ${cls}`} aria-sort={sort.k === k ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
      <button className="label flex items-center gap-1 hover:text-primary-dark" onClick={() => setSort((s) => ({ k, dir: s.k === k ? (s.dir === 1 ? -1 : 1) : -1 }))}>
        {label}{sort.k === k && (sort.dir === 1 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </th>
  );

  return (
    <div className="space-y-8">
      <div className="max-w-2xl">
        <p className="label">Mentor dashboard</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">Review the risky PRs first.</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-muted">Every submission is already scored. Blockers and copy flags float to the top; clean PRs need only a spot-check.</p>
      </div>

      {error && <ErrorCard message={error} onRetry={load} />}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {!stats ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />) : <>
          <StatTile label="PRs reviewed" value={stats.total} sub={`avg score ${stats.avg_score}/5`} />
          <StatTile label="Auto-approved" value={`${stats.auto_approved_pct}%`} tone="ok" sub={`${stats.triage.AUTO_APPROVE} of ${stats.total} PRs`} />
          <StatTile label="Blockers" value={stats.blockers} tone="bad" sub={`${stats.copy_flags} copy flag${stats.copy_flags === 1 ? "" : "s"}`} />
          <StatTile label="Mentor-hours saved" value={stats.hours_saved} sub="modelled: 10 min manual vs AI-assisted" />
        </>}
      </div>

      <section className="card overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by triage">
            {FILTERS.map((f) => (
              <button key={f.v} onClick={() => setFilter(f.v)} aria-pressed={filter === f.v}
                className={`rounded-pill border px-3.5 py-1.5 font-headline text-xs font-bold uppercase tracking-wide transition ${
                  filter === f.v ? "border-primary bg-primary text-white" : "border-primary/40 bg-primary-soft text-primary hover:bg-primary-tint"}`}>{f.label}</button>
            ))}
          </div>
          <div className="relative sm:w-64">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
            <label htmlFor="q" className="sr-only">Search PRs</label>
            <input id="q" className="field !py-2 pl-10" placeholder="Search intern, track, PR…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>

        {!items ? (
          <div className="space-y-2 p-4">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12" />)}</div>
        ) : rows.length === 0 ? (
          <div className="p-6"><EmptyState icon={<Inbox className="h-6 w-6" />} title="Nothing matches" body="No reviewed PRs match this filter yet. Submit one from the Review page or clear the filters."
            action={<button className="btn-ghost" onClick={() => { setFilter("ALL"); setQ(""); }}>Clear filters</button>} /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="border-b border-line bg-cardAlt"><tr>
                {th("priority", "Priority")}<th scope="col" className="px-4 py-3 text-left"><span className="label">Triage</span></th>
                {th("intern", "Intern / PR")}{th("track", "Track")}{th("score", "Score")}<th scope="col" className="px-4 py-3 text-left"><span className="label">Flags</span></th>
              </tr></thead>
              <tbody className="divide-y divide-line">
                {rows.map((i) => (
                  <tr key={i.id} className="cursor-pointer transition hover:bg-primary-tint/60 focus-within:bg-primary-tint/60" onClick={() => setOpen(i.id)}>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2"><span className="w-9 font-headline font-extrabold text-ink">{i.priority}</span>
                        <span className="hidden h-1.5 w-16 overflow-hidden rounded-pill bg-line sm:block" aria-hidden><span className={`block h-full ${i.priority >= 50 ? "bg-bad" : i.priority >= 18 ? "bg-warn" : "bg-ok"}`} style={{ width: `${i.priority}%` }} /></span></div>
                    </td>
                    <td className="px-4 py-3.5"><TriageBadge triage={i.triage} size="sm" /></td>
                    <td className="max-w-[18rem] px-4 py-3.5">
                      <button className="block max-w-full text-left" onClick={(e) => { e.stopPropagation(); setOpen(i.id); }}>
                        <span className="block truncate font-semibold text-ink">{i.title}</span>
                        <span className="hint block truncate">{i.intern} · {i.id}</span>
                      </button>
                    </td>
                    <td className="px-4 py-3.5 text-body">{i.track}</td>
                    <td className="px-4 py-3.5 font-mono text-ink">{i.score.toFixed(1)}</td>
                    <td className="px-4 py-3.5">
                      <div className="flex flex-wrap gap-1.5">
                        {i.critical > 0 && <span className="chip border-bad-line bg-bad-soft text-bad">{i.critical} critical</span>}
                        {i.warnings > 0 && <span className="chip border-warn-line bg-warn-soft text-warn">{i.warnings} warn</span>}
                        {i.similarity_flag && <span className="chip border-warn-line bg-warn-soft text-warn" title={`Similar to ${i.similar_to}`}><Copy className="h-3 w-3" aria-hidden />{Math.round(i.similarity_top * 100)}% copy</span>}
                        {!i.critical && !i.warnings && !i.similarity_flag && <span className="hint">none</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {open && <Drawer id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
