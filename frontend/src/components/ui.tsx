import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { SEVERITY_STYLE, TRIAGE_STYLE } from "../theme";
import type { Severity, Triage } from "../lib/types";

export function TriageBadge({ triage, size = "md" }: { triage: Triage; size?: "sm" | "md" }) {
  const t = TRIAGE_STYLE[triage];
  const Icon = triage === "AUTO_APPROVE" ? CheckCircle2 : triage === "BLOCKER" ? XCircle : AlertTriangle;
  return (
    <span className={`chip ${t.cls} ${size === "md" ? "px-3 py-1 text-xs" : ""}`}>
      <Icon className={size === "md" ? "h-3.5 w-3.5" : "h-3 w-3"} aria-hidden /> {t.label}
    </span>
  );
}

export function SeverityChip({ severity }: { severity: Severity }) {
  return <span className={`chip ${SEVERITY_STYLE[severity]}`}>{severity}</span>;
}

export function ScoreRing({ score, size = 132 }: { score: number; size?: number }) {
  const r = (size - 14) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, score / 5));
  const color = score >= 4 ? "#0F766E" : score >= 3 ? "#9A5B00" : "#BA1A1A";
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`Overall score ${score} out of 5`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E3E8EA" strokeWidth="10" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} style={{ transition: "stroke-dashoffset .8s ease" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-headline text-3xl font-extrabold text-ink">{score.toFixed(1)}</span>
        <span className="hint">out of 5</span>
      </div>
    </div>
  );
}

export function ScoreBar({ label, value }: { label: string; value: number }) {
  const color = value >= 4 ? "bg-ok" : value >= 3 ? "bg-warn" : "bg-bad";
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-sm font-semibold text-ink">{label}</span>
        <span className="font-mono text-xs text-muted">{value}/5</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-pill bg-line" role="progressbar" aria-valuemin={0} aria-valuemax={5} aria-valuenow={value} aria-label={label}>
        <div className={`h-full rounded-pill ${color}`} style={{ width: `${(value / 5) * 100}%`, transition: "width .7s ease" }} />
      </div>
    </div>
  );
}

export function StatTile({ label, value, sub, tone = "default" }: { label: string; value: ReactNode; sub?: string; tone?: "default" | "ok" | "bad" | "warn" }) {
  const tones = { default: "text-ink", ok: "text-ok", bad: "text-bad", warn: "text-warn" };
  return (
    <div className="card p-5">
      <p className="label">{label}</p>
      <p className={`mt-2 font-headline text-3xl font-extrabold ${tones[tone]}`}>{value}</p>
      {sub && <p className="hint mt-1">{sub}</p>}
    </div>
  );
}

export function EmptyState({ icon, title, body, action }: { icon: ReactNode; title: string; body: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary-soft text-primary">{icon}</div>
      <h3 className="text-lg font-extrabold">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorCard({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-panel border border-bad-line bg-bad-soft p-4 text-bad">
      <XCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div className="flex-1">
        <p className="font-headline text-sm font-extrabold">Something went wrong</p>
        <p className="mt-0.5 text-sm">{message}</p>
      </div>
      {onRetry && <button onClick={onRetry} className="btn-ghost !border-bad-line !bg-white !text-bad">Retry</button>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-panel bg-line/70 ${className}`} aria-hidden />;
}
