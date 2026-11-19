import { useEffect, useRef, useState } from "react";
import { Check, FileText, GitPullRequest, Loader2, ScanSearch, X } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { Health, ReviewResponse, SampleMeta } from "../lib/types";
import ReviewResult from "../components/ReviewResult";
import { ErrorCard } from "../components/ui";

const STEPS = ["Parsing diff", "Static checks", "LLM rubric review", "Similarity scan", "Triage"];

function PipelineLoader() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(x + 1, STEPS.length - 1)), 750);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="card rise p-6 sm:p-8" role="status" aria-live="polite">
      <p className="label">Reviewing your PR</p>
      <ol className="mt-5 grid gap-3 sm:grid-cols-5">
        {STEPS.map((s, k) => {
          const done = k < i, active = k === i;
          return (
            <li key={s} className={`flex items-center gap-3 rounded-panel border p-3 transition ${
              active ? "border-primary bg-primary-tint" : done ? "border-ok-line bg-ok-soft" : "border-line bg-cardAlt opacity-70"}`}>
              <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${done ? "bg-ok text-white" : active ? "bg-primary text-white" : "bg-line text-muted"}`}>
                {done ? <Check className="h-4 w-4" strokeWidth={3} /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : <span className="font-mono text-xs">{k + 1}</span>}
              </span>
              <span className="text-sm font-semibold text-ink">{s}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default function Review() {
  const [health, setHealth] = useState<Health | null>(null);
  const [samples, setSamples] = useState<SampleMeta[]>([]);
  const [mode, setMode] = useState<"url" | "diff">("url");
  const [url, setUrl] = useState("");
  const [diff, setDiff] = useState("");
  const [track, setTrack] = useState("");
  const [week, setWeek] = useState("");
  const [intern, setIntern] = useState("");
  const [sample, setSample] = useState<SampleMeta | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReviewResponse | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.health().then((h) => { setHealth(h); setTrack((t) => t || h.tracks[0]); setWeek((w) => w || h.weeks[0]); }).catch((e) => setError(e.message));
    api.samples().then(setSamples).catch(() => undefined);
  }, []);

  const pick = (s: SampleMeta) => {
    setSample(s); setTrack(s.track); setWeek(s.week); setError(null); setUrl(""); setDiff("");
  };

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!sample && mode === "url" && !url.trim()) return setError("Paste a public GitHub PR URL, e.g. https://github.com/owner/repo/pull/123, or pick a sample below.");
    if (!sample && mode === "diff" && !diff.trim()) return setError("Paste the output of `git diff` (unified diff), or pick a sample below.");
    setBusy(true); setResult(null);
    try {
      const body = sample ? { sample_id: sample.id, track, week }
        : mode === "url" ? { pr_url: url.trim(), track, week, intern: intern || undefined }
        : { diff, track, week, intern: intern || undefined };
      const wait = new Promise((res) => setTimeout(res, 2300)); // let the pipeline animation play even when the reviewer is instant
      const [r] = await Promise.all([api.review(body), wait]);
      setResult(r);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unexpected error. Please try again.");
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-8">
      <div className="max-w-2xl">
        <p className="label">Intern view</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">Get a mentor-grade review in seconds.</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-muted">
          Submit today's pull request. BitReview AI scores it against the BitElevate roadmap, points to the exact lines to fix, and tells your mentor how urgently it needs a human.
        </p>
      </div>

      <form onSubmit={run} className="card space-y-6 p-6 sm:p-8" aria-label="Submit a pull request for review">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div role="tablist" aria-label="Input type" className="flex gap-2">
            {([["url", "PR URL", GitPullRequest], ["diff", "Or paste diff", FileText]] as const).map(([m, label, Icon]) => (
              <button key={m} type="button" role="tab" aria-selected={mode === m && !sample} onClick={() => { setMode(m); setSample(null); }}
                className={`flex items-center gap-2 rounded-pill border px-4 py-2 font-headline text-xs font-bold uppercase tracking-wider transition ${
                  mode === m && !sample ? "border-primary bg-primary text-white" : "border-primary/40 bg-primary-soft text-primary hover:bg-primary-tint"}`}>
                <Icon className="h-4 w-4" aria-hidden />{label}
              </button>
            ))}
          </div>
          <p className="hint">{health?.mode === "mock" ? "Demo mode: rule-based reviewer, no API key set" : health ? "Live LLM review" : ""}</p>
        </div>

        {sample ? (
          <div className="flex items-center gap-3 rounded-panel border border-primary/30 bg-primary-tint p-4">
            <FileText className="h-5 w-5 shrink-0 text-primary" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="label">Sample PR loaded</p>
              <p className="truncate text-sm font-semibold text-ink">{sample.title}</p>
              <p className="hint truncate">{sample.id} · by {sample.intern}</p>
            </div>
            <button type="button" onClick={() => setSample(null)} aria-label="Clear sample" className="rounded-full p-2 text-muted hover:text-ink"><X className="h-4 w-4" /></button>
          </div>
        ) : mode === "url" ? (
          <div>
            <label htmlFor="pr-url" className="label">Pull request URL</label>
            <input id="pr-url" className="field mt-2" value={url} onChange={(e) => setUrl(e.target.value)} inputMode="url" autoComplete="off"
              placeholder="https://github.com/owner/repo/pull/123" aria-describedby="pr-url-hint" />
            <p id="pr-url-hint" className="hint mt-2">Public repositories only. Private repo? Use “Or paste diff”.</p>
          </div>
        ) : (
          <div>
            <label htmlFor="diff" className="label">Unified diff</label>
            <textarea id="diff" rows={9} value={diff} onChange={(e) => setDiff(e.target.value)} spellCheck={false}
              className="mt-2 w-full rounded-card border border-line bg-white px-5 py-4 font-mono text-xs leading-6 text-ink transition focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder={"diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1,3 +1,4 @@\n..."} aria-describedby="diff-hint" />
            <p id="diff-hint" className="hint mt-2">Run <span className="text-ink">git diff main...HEAD</span> and paste the output.</p>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="track" className="label">Track</label>
            <select id="track" className="field mt-2" value={track} onChange={(e) => setTrack(e.target.value)}>
              {(health?.tracks ?? [track]).map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="week" className="label">Roadmap stage</label>
            <select id="week" className="field mt-2" value={week} onChange={(e) => setWeek(e.target.value)}>
              {(health?.weeks ?? [week]).map((w) => <option key={w}>{w}</option>)}
            </select>
          </div>
          {!sample && (
            <div className="sm:col-span-3">
              <label htmlFor="intern" className="label block">Your handle <span className="font-mono normal-case tracking-normal text-muted">(optional)</span></label>
              <input id="intern" className="field mt-2 sm:max-w-sm" value={intern} onChange={(e) => setIntern(e.target.value)} placeholder="first.last" autoComplete="off" />
            </div>
          )}
        </div>

        <div>
          <p className="label">No PR handy? Try a sample</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {samples.length === 0 && <span className="hint">Loading samples…</span>}
            {samples.map((s) => (
              <button key={s.id} type="button" onClick={() => pick(s)} title={s.title} aria-pressed={sample?.id === s.id}
                className={`rounded-pill border px-3.5 py-1.5 font-mono text-xs transition ${
                  sample?.id === s.id ? "border-primary bg-primary text-white" : "border-primary/40 bg-primary-soft text-primary hover:bg-primary-tint"}`}>
                {s.id.replace(/^s\d+-/, "")}
              </button>
            ))}
          </div>
        </div>

        {error && <ErrorCard message={error} />}

        <button type="submit" className="btn-primary w-full sm:w-auto" disabled={busy || !health}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ScanSearch className="h-4 w-4" aria-hidden />}
          {busy ? "Reviewing…" : "Run AI review"}
        </button>
      </form>

      <div ref={resultRef} className="scroll-mt-24">
        {busy && <PipelineLoader />}
        {!busy && result && <ReviewResult r={result} />}
      </div>
    </div>
  );
}
