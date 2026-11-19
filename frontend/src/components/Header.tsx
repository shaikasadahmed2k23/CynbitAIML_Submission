import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { Check, Menu, X } from "lucide-react";
import { api } from "../lib/api";
import type { Health } from "../lib/types";

export function Logo() {
  return (
    <span className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white shadow-lift" aria-hidden>
        <Check className="h-5 w-5" strokeWidth={3.2} />
      </span>
      <span className="leading-none">
        <span className="block font-headline text-[17px] font-extrabold text-ink">BitReview AI</span>
        <span className="hint block !text-[10px] uppercase tracking-[0.18em]">for BitElevate</span>
      </span>
    </span>
  );
}

const NAV = [
  { to: "/", label: "Review", end: true },
  { to: "/queue", label: "Mentor Queue" },
  { to: "/how", label: "How it works" },
];

export default function Header() {
  const [health, setHealth] = useState<Health | null>(null);
  const [offline, setOffline] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => { api.health().then(setHealth).catch(() => setOffline(true)); }, []);

  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-pill px-4 py-2 font-headline text-xs font-bold uppercase tracking-wider transition ${
      isActive ? "bg-primary-soft text-primary" : "text-muted hover:text-ink"}`;

  const badge = offline ? { t: "Offline", c: "border-bad-line bg-bad-soft text-bad", d: "bg-bad" }
    : !health ? { t: "…", c: "border-line bg-cardAlt text-muted", d: "bg-muted" }
    : health.mode === "live" ? { t: "Live model", c: "border-ok-line bg-ok-soft text-ok", d: "bg-ok" }
    : { t: "Demo mode", c: "border-warn-line bg-warn-soft text-warn", d: "bg-warn" };

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-page/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <NavLink to="/" aria-label="BitReview AI home" className="rounded-xl"><Logo /></NavLink>
        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV.map((n) => <NavLink key={n.to} to={n.to} end={n.end} className={link}>{n.label}</NavLink>)}
        </nav>
        <div className="flex items-center gap-2">
          <span className={`chip ${badge.c}`} title={health ? `Providers: ${health.providers.join(", ") || "none (rule-based demo reviewer)"}` : undefined}>
            <span className={`h-1.5 w-1.5 rounded-full ${badge.d}`} aria-hidden />{badge.t}
          </span>
          <button className="rounded-full p-2 text-ink md:hidden" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      {open && (
        <nav className="flex flex-col gap-1 border-t border-line px-4 py-3 md:hidden" aria-label="Mobile">
          {NAV.map((n) => <NavLink key={n.to} to={n.to} end={n.end} className={link} onClick={() => setOpen(false)}>{n.label}</NavLink>)}
        </nav>
      )}
    </header>
  );
}
