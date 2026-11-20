import { BookOpen, FileSearch, GitBranch, Gauge, ListOrdered, ScanLine, ShieldCheck, Sparkles, Copy, ExternalLink } from "lucide-react";
import type { ReactNode } from "react";

const REPO = (import.meta.env.VITE_REPO_URL as string | undefined)?.replace(/\/$/, "");

const STEPS: { icon: ReactNode; title: string; body: string; file: string }[] = [
  { icon: <GitBranch />, title: "1 · Ingest", body: "Fetch a public PR through the GitHub REST API (or take a pasted diff) with the intern's track and roadmap stage.", file: "github.py" },
  { icon: <FileSearch />, title: "2 · Parse", body: "Unified diff becomes files, hunks and exact line numbers, so every comment can be anchored to a real line.", file: "diff_parser.py" },
  { icon: <ScanLine />, title: "3 · Static checks", body: "Millisecond heuristics: leaked secrets, SQL injection, missing tests, N+1 queries, thread races, debug leftovers, commit hygiene.", file: "static_checks.py" },
  { icon: <Sparkles />, title: "4 · LLM rubric review", body: "Groq gpt-oss-120b (Gemini 2.5 flash fallback, deterministic demo fallback) scores five rubric areas as strict, validated JSON. Comments on lines that don't exist are dropped.", file: "llm_reviewer.py" },
  { icon: <Copy />, title: "5 · Copy detection", body: "TF-IDF over character n-grams of normalized code. Renaming variables or editing comments doesn't hide a copied PR.", file: "similarity.py" },
  { icon: <ListOrdered />, title: "6 · Triage", body: "Static, LLM and similarity signals merge into a priority score. The LLM can never wave through a critical finding.", file: "triage.py" },
];

const ROI = [
  { k: "42,000", v: "PRs per 1,000-intern cohort", s: "1 PR × 42 working days" },
  { k: "5,460 h", v: "mentor time saved", s: "78% less than 10 min/PR manual review" },
  { k: "≈ $31", v: "AI cost for the cohort", s: "about $0.0009 per PR, measured on Groq gpt-oss-120b" },
  { k: "< 3 s", v: "to first feedback", s: "instead of waiting for a mentor" },
];

function ReportLink({ href, children }: { href: string; children: ReactNode }) {
  return <a href={href} target="_blank" rel="noreferrer" className="btn-ghost">{children}<ExternalLink className="h-3.5 w-3.5" aria-hidden /></a>;
}

export default function How() {
  return (
    <div className="space-y-12">
      <div className="max-w-2xl">
        <p className="label">How it works</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">From a pull request to a prioritized queue.</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-muted">
          BitElevate interns submit a PR every day and 1000+ interns means thousands of reviews. BitReview AI does the first pass so mentors spend their time on judgement, not on spotting a leaked key.
        </p>
      </div>

      <section aria-labelledby="pipe">
        <h2 id="pipe" className="label mb-4">The pipeline</h2>
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.title} className="card flex flex-col p-6 transition hover:shadow-lift">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-soft text-primary [&>svg]:h-5 [&>svg]:w-5" aria-hidden>{s.icon}</span>
              <h3 className="mt-4 text-base font-extrabold">{s.title}</h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-muted">{s.body}</p>
              <p className="hint mt-4">app/core/{s.file}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="guard" className="card grid gap-6 p-6 sm:p-8 md:grid-cols-3">
        <div className="md:col-span-1">
          <ShieldCheck className="h-6 w-6 text-primary" aria-hidden />
          <h2 id="guard" className="mt-3 text-lg font-extrabold">Guardrails, in code</h2>
        </div>
        <ul className="space-y-2 text-sm text-body md:col-span-2">
          <li>• Schema-validated output; invalid JSON falls through Groq → Gemini → rule-based demo reviewer, so the product never errors out.</li>
          <li>• PR text is treated as untrusted: instructions hidden in code comments can't change the verdict.</li>
          <li>• Hallucinated file or line references are discarded before an intern ever sees them.</li>
          <li>• AI only escalates or approves. Mentors keep the final say and every copy flag is a conversation, not a penalty.</li>
        </ul>
      </section>

      <section aria-labelledby="roi">
        <h2 id="roi" className="label mb-4">The business case</h2>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {ROI.map((r) => (
            <div key={r.v} className="card p-5">
              <p className="font-headline text-3xl font-extrabold text-primary">{r.k}</p>
              <p className="mt-1 text-sm font-semibold text-ink">{r.v}</p>
              <p className="hint mt-1">{r.s}</p>
            </div>
          ))}
        </div>
        <p className="hint mt-3 flex items-start gap-2"><Gauge className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          Modelled, not measured: assumes 1,000 interns, 42 working days, 10 min manual review, 40% auto-approved (1 min) and 60% escalated (3 min), and $8/h mentor cost. Assumptions are listed in the opportunity report.</p>
      </section>

      <section aria-labelledby="docs" className="card p-6 sm:p-8">
        <BookOpen className="h-6 w-6 text-primary" aria-hidden />
        <h2 id="docs" className="mt-3 text-lg font-extrabold">Read more</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <ReportLink href="/reports/AI_Opportunity_Report.md">AI Opportunity Report</ReportLink>
          <ReportLink href="/reports/Technical_Approach.md">Technical Approach</ReportLink>
          <ReportLink href="/reports/results.md">Evaluation results</ReportLink>
          {REPO && <ReportLink href={REPO}>GitHub repository</ReportLink>}
        </div>
      </section>
    </div>
  );
}
