/**
 * Design tokens extracted from https://www.cynbit.in (compiled Tailwind CSS custom properties):
 *   --color-primary #006067, --color-primary-container #007b83, --color-on-surface #181c1d,
 *   --color-surface #f7fafa, --font-headline "Plus Jakarta Sans", --font-body "Manrope",
 *   --radius-2xl 2rem, --radius-3xl 2.5rem, --radius-full 9999px.
 * Component styling (pill buttons, #DDEEEA secondary pills, 1px bordered cards, uppercase labels,
 * monospace hints, page bg #F4F7F8) follows Cynbit's candidate-portal spec.
 */
export const theme = {
  colors: {
    primary: { DEFAULT: "#006067", container: "#007b83", dark: "#004d53", soft: "#DDEEEA", tint: "#EEF7F5" },
    page: "#F4F7F8",
    card: "#FFFFFF",
    cardAlt: "#F8FAFB",
    line: "#E3E8EA",
    ink: "#1E293B",
    body: "#334155",
    muted: "#64748B",
    ok: { DEFAULT: "#0F766E", soft: "#DCF3EE", line: "#A7DDD2" },
    warn: { DEFAULT: "#9A5B00", soft: "#FFF1DA", line: "#F2CF94" },
    bad: { DEFAULT: "#BA1A1A", soft: "#FFE9E6", line: "#F3B5AE" },
    info: { DEFAULT: "#12629D", soft: "#E3F0FB", line: "#B5D4EE" },
  },
  fonts: {
    headline: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
    sans: ['"Manrope"', "system-ui", "sans-serif"],
    mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
  },
  radius: { card: "1.5rem", panel: "1.25rem", pill: "9999px" },
  shadow: {
    soft: "0 1px 2px rgba(15,23,42,.04), 0 8px 24px -12px rgba(15,23,42,.10)",
    lift: "0 2px 4px rgba(15,23,42,.05), 0 18px 40px -16px rgba(0,96,103,.22)",
  },
} as const;

export const TRIAGE_STYLE = {
  AUTO_APPROVE: { label: "Auto-approve", cls: "bg-ok-soft text-ok border-ok-line", dot: "bg-ok" },
  NEEDS_MENTOR: { label: "Needs mentor", cls: "bg-warn-soft text-warn border-warn-line", dot: "bg-warn" },
  BLOCKER: { label: "Blocker", cls: "bg-bad-soft text-bad border-bad-line", dot: "bg-bad" },
} as const;

export const SEVERITY_STYLE = {
  critical: "bg-bad-soft text-bad border-bad-line",
  warning: "bg-warn-soft text-warn border-warn-line",
  info: "bg-info-soft text-info border-info-line",
} as const;
