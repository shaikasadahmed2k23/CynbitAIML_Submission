import { Fragment, useMemo, useState } from "react";
import { AlertOctagon, Clock, Copy, Cpu, FileCode2, ListChecks, ShieldAlert } from "lucide-react";
import type { DiffFile, InlineComment, ReviewResponse } from "../lib/types";
import { highlight } from "../lib/highlight";
import { nextSteps } from "../lib/nextSteps";
import { ScoreBar, ScoreRing, SeverityChip, TriageBadge } from "./ui";

const RUBRIC: [keyof ReviewResponse["review"]["scores"], string][] = [
  ["correctness", "Correctness"], ["code_quality", "Code quality"], ["security", "Security"],
  ["testing", "Testing"], ["roadmap_alignment", "Roadmap alignment"],
];

const providerLabel = (m: ReviewResponse["meta"]) => (m.provider === "groq" ? "Groq" : m.provider === "gemini" ? "Gemini" : m.demo_fallback ? "Demo fallback" : "Demo mode");

function FileSnippet({ file, comments }: { file: DiffFile; comments: InlineComment[] }) {
  const [all, setAll] = useState(false);
  const byLine = useMemo(() => {
    const m = new Map<number, InlineComment[]>();
    comments.forEach((c) => m.set(c.line, [...(m.get(c.line) ?? []), c]));
    return m;
  }, [comments]);
  const shown = useMemo(() => {
    if (all) return file.lines.map((_, i) => i);
    const keep = new Set<number>();
    file.lines.forEach((l, i) => { if (l.kind !== "del" && l.n != null && byLine.has(l.n)) for (let k = i - 2; k <= i + 2; k++) keep.add(k); });
    return [...keep].filter((i) => i >= 0 && i < file.lines.length).sort((a, b) => a - b);
  }, [all, file.lines, byLine]);

  return (
    <div className="overflow-hidden rounded-panel border border-line bg-cardAlt">
      <div className="flex items-center justify-between gap-2 border-b border-line bg-white px-4 py-2.5">
        <span className="flex min-w-0 items-center gap-2 font-mono text-xs font-medium text-ink">
          <FileCode2 className="h-4 w-4 shrink-0 text-primary" aria-hidden /> <span className="truncate">{file.path}</span>
        </span>
        <button onClick={() => setAll((v) => !v)} className="hint shrink-0 rounded-pill px-2 py-1 underline-offset-2 hover:underline">
          {all ? "Show only commented lines" : "Show full file"}
        </button>
      </div>
      <div className="overflow-x-auto py-1 font-mono text-[12.5px] leading-6">
        {shown.map((i, idx) => {
          const l = file.lines[i];
          const gap = idx > 0 && i - shown[idx - 1] > 1;
          const cs = l.kind !== "del" && l.n != null ? byLine.get(l.n) : undefined;
          const bg = cs ? "bg-warn-soft/80" : l.kind === "add" ? "bg-ok-soft/60" : l.kind === "del" ? "bg-bad-soft/60" : "";
          return (
            <Fragment key={i}>
              {gap && <div className="hint px-4 py-0.5 text-center">⋯</div>}
              <div className={`flex ${bg}`}>
                <span className="w-12 shrink-0 select-none pr-3 text-right text-muted/70">{l.n ?? ""}</span>
                <span className="w-4 shrink-0 select-none text-muted">{l.kind === "add" ? "+" : l.kind === "del" ? "−" : ""}</span>
                <code className="whitespace-pre pr-4 text-ink">{highlight(l.text)}</code>
              </div>
              {cs?.map((c, k) => (
                <div key={k} className="my-1.5 ml-16 mr-3 rounded-panel border border-line bg-white p-3 font-sans text-sm shadow-soft">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityChip severity={c.severity} /> <span className="hint">line {c.line}</span>
                  </div>
                  <p className="mt-1.5 text-body">{c.comment}</p>
                  {c.suggestion && (
                    <p className="mt-2 rounded-xl bg-primary-tint px-3 py-2 font-mono text-xs text-primary-dark">
                      <span className="font-bold">Suggestion: </span>{c.suggestion}
                    </p>
                  )}
                </div>
              ))}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}

export default function ReviewResult({ r }: { r: ReviewResponse }) {
  const steps = useMemo(() => nextSteps(r), [r]);
  const [done, setDone] = useState<Set<number>>(new Set());
  const grouped = useMemo(() => {
    const m = new Map<string, InlineComment[]>();
    r.review.inline_comments.forEach((c) => m.set(c.file, [...(m.get(c.file) ?? []), c]));
    return [...m.entries()];
  }, [r]);

  return (
    <div className="rise space-y-6">
      {/* headline */}
      <section className="card p-6 sm:p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <ScoreRing score={r.review.overall_score} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <TriageBadge triage={r.final_triage} />
              <span className="chip border-line bg-cardAlt text-muted">Priority {r.priority}</span>
              <span className="chip border-line bg-cardAlt text-muted">{r.critical} critical · {r.warnings} {r.warnings === 1 ? "warning" : "warnings"} · {r.info} info</span>
            </div>
            <h2 className="mt-3 break-words text-xl font-extrabold sm:text-2xl">{r.title}</h2>
            <p className="hint mt-1">{r.id} · {r.n_files} file{r.n_files === 1 ? "" : "s"} · +{r.added}/−{r.removed} · {r.languages.join(", ") || "n/a"} · by {r.intern}</p>
            <p className="mt-3 text-[15px] leading-relaxed text-body">{r.review.summary}</p>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-t border-line pt-4">
          <span className="chip border-primary/30 bg-primary-tint text-primary-dark" title="Provider and measured end-to-end pipeline time">
            <Cpu className="h-3.5 w-3.5" aria-hidden />
            {r.cached ? `Cached · ${(r.served_in_s ?? 0).toFixed(2)}s` : `${providerLabel(r.meta)} · ${r.pipeline_latency_s.toFixed(1)}s`}
          </span>
          <span className="hint flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" aria-hidden />{r.cached ? `originally ${providerLabel(r.meta)} · ${r.meta.provider === "mock" ? "rule-based" : r.meta.model} · ${r.pipeline_latency_s.toFixed(1)}s` : r.meta.provider === "mock" ? (r.meta.demo_fallback ? "LLM providers unavailable or timed out, rule-based review shown" : "rule-based demo reviewer, no LLM call") : `${r.meta.model} · LLM call ${r.meta.latency_s.toFixed(1)}s (measured, not simulated)`}</span>
          <span className="hint flex items-center gap-1.5"><ListChecks className="h-3.5 w-3.5" aria-hidden />~{r.minutes_saved} mentor-min saved</span>
          {r.meta.cost_usd > 0 && <span className="hint">${r.meta.cost_usd.toFixed(5)} LLM cost</span>}
          {r.meta.dropped_comments > 0 && <span className="hint">{r.meta.dropped_comments} unverifiable AI {r.meta.dropped_comments === 1 ? "comment" : "comments"} dropped</span>}
        </div>
        {r.meta.fallback_errors.length > 0 && (
          <p className="hint mt-3 rounded-xl bg-warn-soft px-3 py-2 !text-warn">Fell back after provider error: {r.meta.fallback_errors.join(" | ")}</p>
        )}
      </section>

      {r.similarity_flag && (
        <section role="alert" className="flex items-start gap-4 rounded-card border border-warn-line bg-warn-soft p-5">
          <Copy className="mt-0.5 h-6 w-6 shrink-0 text-warn" aria-hidden />
          <div>
            <p className="font-headline text-sm font-extrabold uppercase tracking-wide text-warn">Possible copied submission</p>
            <p className="mt-1 text-sm text-body">
              This PR's code is <b>{Math.round(r.similarity_top * 100)}%</b> similar to <span className="font-mono">{r.similar_to}</span> even after normalizing
              variable names and comments. This is a flag for a mentor conversation, not an accusation.
            </p>
          </div>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="card p-6 lg:col-span-3">
          <p className="label">Rubric scores</p>
          <div className="mt-4 space-y-4">
            {RUBRIC.map(([k, label]) => <ScoreBar key={k} label={label} value={r.review.scores[k]} />)}
          </div>
        </section>
        <section className="card p-6 lg:col-span-2">
          <p className="label">Next steps for you</p>
          <ul className="mt-4 space-y-2.5">
            {steps.map((s, i) => (
              <li key={i}>
                <label className="flex cursor-pointer items-start gap-3 text-sm">
                  <input type="checkbox" checked={done.has(i)} className="mt-1 h-4 w-4 shrink-0 accent-primary"
                    onChange={() => setDone((d) => { const n = new Set(d); n.has(i) ? n.delete(i) : n.add(i); return n; })} />
                  <span className={done.has(i) ? "text-muted line-through" : "text-body"}>{s}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="card p-6">
        <p className="label">Inline comments</p>
        {grouped.length === 0 ? (
          <p className="mt-3 text-sm text-muted">No line-level comments. {r.final_triage === "AUTO_APPROVE" ? "Clean change." : "See static findings below."}</p>
        ) : (
          <div className="mt-4 space-y-5">
            {grouped.map(([path, cs]) => {
              const file = r.diff_files.find((f) => f.path === path);
              return file ? <FileSnippet key={path} file={file} comments={cs} /> : (
                <div key={path} className="rounded-panel border border-line p-4">
                  <p className="font-mono text-xs">{path}</p>
                  {cs.map((c, i) => <p key={i} className="mt-2 text-sm"><SeverityChip severity={c.severity} /> line {c.line}: {c.comment}</p>)}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="card p-6">
        <p className="label">Static findings</p>
        {r.findings.length === 0 ? (
          <p className="mt-3 text-sm text-muted">No heuristic issues detected.</p>
        ) : (
          <ul className="mt-4 divide-y divide-line">
            {r.findings.map((f, i) => (
              <li key={i} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 text-sm">
                <SeverityChip severity={f.severity} />
                <span className="font-mono text-xs font-medium text-ink">{f.rule}</span>
                <span className="min-w-0 flex-1 text-body">{f.message}</span>
                {f.file && <span className="hint">{f.file}{f.line ? `:${f.line}` : ""}</span>}
              </li>
            ))}
          </ul>
        )}
        {r.reasons.length > 0 && (
          <p className="hint mt-4 flex items-start gap-2"><ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />Triage reasoning: {r.reasons.join("; ")}</p>
        )}
        {r.final_triage === "BLOCKER" && (
          <p className="mt-3 flex items-start gap-2 text-sm font-semibold text-bad"><AlertOctagon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />Fix the critical issues before this PR can be merged.</p>
        )}
      </section>
    </div>
  );
}
