"""Evaluate the pipeline on labeled PRs and (re)generate eval/results.md.

Two evaluation sets:
  * synthetic : data/samples/       10 hand-written PRs with seeded issues (also the demo data)
  * real      : data/eval_real/     real, merged public GitHub PRs pinned by URL, labeled by criteria in eval/LABELING.md

Two reviewers:
  * mock : deterministic rule-based reviewer (baseline; no network)
  * live : the configured LLM chain (Groq -> Gemini), keys read from the environment / .env

Usage:
    python eval/run_eval.py --mock     # run the mock baseline, save eval/mock_results.json
    python eval/run_eval.py --live     # run live model,        save eval/live_results.json
    python eval/run_eval.py            # --live if an API key is configured, else --mock
Each run re-renders eval/results.md from whatever result files exist, so the two tables stay separate.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app.core import llm_reviewer  # noqa: E402
from app.core.llm_reviewer import get_secret  # noqa: E402
from app.core.pipeline import SAMPLES_DIR, Store, analyze, load_samples  # noqa: E402
from app.core.similarity import DEFAULT_THRESHOLD  # noqa: E402

EVAL = ROOT / "eval"
REAL_DIR = ROOT / "data" / "eval_real"


def detected(rule: str, sub) -> bool:
    if rule == "copied":
        return sub.similarity_top >= DEFAULT_THRESHOLD
    if any(f["rule"] == rule for f in sub.findings):
        return True
    # a live LLM may also catch it in a comment/summary
    text = (sub.review.summary + " " + " ".join(c.comment for c in sub.review.inline_comments)).lower()
    kw = {"sql-injection": "sql", "hardcoded-secret": "secret", "missing-tests": "test", "n-plus-one": "n+1",
          "race-condition": "race"}
    return rule in kw and kw[rule] in text


def load_set(name: str) -> tuple[list[dict], Path]:
    if name == "synthetic":
        return load_samples(), SAMPLES_DIR
    p = REAL_DIR / "manifest.json"
    return (json.loads(p.read_text(encoding="utf-8")) if p.exists() else []), REAL_DIR


def run_set(name: str, live: bool) -> dict:
    items, folder = load_set(name)
    store = Store(Path(tempfile.mkdtemp()) / "eval_store.json")
    rows = []
    for m in items:
        diff = (folder / f"{m['id']}.diff").read_text(encoding="utf-8")
        sub = analyze(diff, m["track"], m["week"], store, title=m["title"], commits=m.get("commits", []),
                      intern=m.get("intern", "eval"), source="sample", sub_id=m["id"], force_mock=not live)
        hits = {r: detected(r, sub) for r in m.get("seeded", [])}
        rows.append({
            "id": m["id"], "seeded": list(hits), "detected": hits, "expected": m["expected_triage"],
            "got": sub.final_triage, "ok": sub.final_triage == m["expected_triage"], "score": sub.review.overall_score,
            "latency_s": sub.pipeline_latency_s, "llm_latency_s": sub.meta.latency_s, "cost_usd": sub.meta.cost_usd,
            "provider": f"{sub.meta.provider}/{sub.meta.model}", "dropped": sub.meta.dropped_comments,
            "n_comments": len(sub.review.inline_comments), "errors": sub.meta.fallback_errors,
            "reasons": sub.reasons, "summary": sub.review.summary, "url": m.get("url", ""),
            "note": m.get("label_note", ""),
        })
    return {"set": name, "rows": rows}


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    seeded = sum(len(r["seeded"]) for r in rows)
    hit = sum(sum(r["detected"].values()) for r in rows)
    clean = [r for r in rows if r["expected"] == "AUTO_APPROVE"]
    lat = sorted(r["latency_s"] for r in rows)
    return {
        "n": n, "seeded": seeded, "hit": hit, "tri_ok": sum(r["ok"] for r in rows),
        "clean_n": len(clean), "clean_fp": sum(r["got"] != "AUTO_APPROVE" for r in clean),
        "missed_blockers": sum(r["expected"] == "BLOCKER" and r["got"] != "BLOCKER" for r in rows),
        "lat_avg": sum(lat) / n if n else 0, "lat_p50": lat[n // 2] if n else 0, "lat_max": lat[-1] if n else 0,
        "cost_avg": sum(r["cost_usd"] for r in rows) / n if n else 0,
        "fallbacks": sum(1 for r in rows if r["errors"]),
        "providers": sorted({r["provider"] for r in rows}),
        "dropped": sum(r["dropped"] for r in rows),
    }


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} = {a / b:.0%}" if b else "n/a"


def _lat(s: dict) -> str:
    return f"{s['lat_avg']:.2f} / {s['lat_p50']:.2f} / {s['lat_max']:.2f}"


def render_summary(title: str, data: dict | None, live: bool) -> list[str]:
    if not data:
        return [f"### {title}", "", "_Not run yet._", ""]
    cols = {}
    for k in ("synthetic", "real"):
        rows = data["sets"].get(k, {}).get("rows", [])
        cols[k] = summarize(rows) if rows else None

    def row(label: str, fn, real_na: str | None = None) -> str:
        syn = fn(cols["synthetic"]) if cols["synthetic"] else "n/a"
        rl = real_na if real_na else (fn(cols["real"]) if cols["real"] else "n/a")
        return f"| {label} | {syn} | {rl} |"

    out = [f"### {title}", "", "| Metric | Synthetic (10 seeded PRs) | Real GitHub PRs |", "|---|---|---|",
           row("PRs evaluated", lambda s: s["n"]),
           row("Seeded-issue detection", lambda s: _pct(s["hit"], s["seeded"]), "not applicable (no seeded issues)"),
           row("Triage accuracy", lambda s: _pct(s["tri_ok"], s["n"])),
           row("False escalations on AUTO_APPROVE-labeled PRs", lambda s: _pct(s["clean_fp"], s["clean_n"])),
           row("Missed blockers", lambda s: s["missed_blockers"]),
           row("Latency avg / p50 / max (s per PR, whole pipeline)", _lat),
           row("Cost per PR (from token usage)", lambda s: f"${s['cost_avg']:.5f}")]
    if live:
        out += [row("PRs that fell back to another provider / mock", lambda s: s["fallbacks"]),
                row("Hallucinated comments dropped by the line guard", lambda s: s["dropped"])]
    prov = sorted({p for c in cols.values() if c for p in c["providers"]})
    return out + ["", f"_Run on {data['date']}. Reviewer(s) actually used: {', '.join(prov)}._", ""]


def render_rows(title: str, data: dict | None) -> list[str]:
    if not data:
        return []
    out = [f"### {title}", "", "| Set | Sample | Seeded | Detected | Expected | Got | OK | Score | Latency (s) | Provider |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("synthetic", "real"):
        for r in data["sets"].get(k, {}).get("rows", []):
            det = ", ".join(f"{a}{'✓' if h else '✗'}" for a, h in r["detected"].items()) or "-"
            out.append(f"| {k} | {r['id']} | {', '.join(r['seeded']) or '(clean)'} | {det} | {r['expected']} | {r['got']} | "
                       f"{'✓' if r['ok'] else '✗'} | {r['score']} | {r['latency_s']:.2f} | {r['provider']} |")
    return out + [""]


def render_failures(data: dict | None) -> list[str]:
    if not data:
        return []
    out = []
    for sname in ("synthetic", "real"):
        for r in data["sets"].get(sname, {}).get("rows", []):
            probs = []
            if not r["ok"]:
                probs.append(f"triage {r['got']} instead of {r['expected']}. Reasons: {'; '.join(r['reasons']) or 'n/a'}")
            probs += [f"missed `{a}`" for a, h in r["detected"].items() if not h]
            if r["errors"]:
                probs.append("provider error → " + " | ".join(e[:110] for e in r["errors"]))
            if r["dropped"]:
                probs.append(f"{r['dropped']} comment(s) dropped by the hallucination guard")
            if probs:
                out.append(f"- **{r['id']}** ({sname}): " + "; ".join(probs))
    return out or ["- none observed in this run"]


def render() -> None:
    def ld(n):
        p = EVAL / n
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    mock, live = ld("mock_results.json"), ld("live_results.json")
    out = ["# Evaluation results", "",
           "Two reviewers are measured separately on the same labeled PRs. **The mock baseline is a rule-based reviewer "
           "(deterministic layers only); the live results use a real LLM and are the numbers to trust for model quality.** "
           "Regenerate with `python eval/run_eval.py --mock` and `python eval/run_eval.py --live`.", "",
           "## Labeled sets", "",
           "- **Synthetic (10 PRs):** hand-written in `data/build_samples.py` with seeded issues (11 in total), including one "
           "renamed copy. The mock heuristics were written by the same author, so mock detection here is optimistic by construction.",
           "- **Real GitHub PRs:** merged public PRs pinned by URL in `data/build_eval_real.py` (diffs in `data/eval_real/`), "
           "labeled by me with the criteria in [`LABELING.md`](LABELING.md) before running any reviewer. Labels are one "
           "person's judgement, not ground truth, and the set is tiny.", "",
           "## Mock baseline (rule-based, no LLM)", ""]
    out += render_summary("Mock baseline summary", mock, False)
    cfg = ", ".join(sorted({r["provider"] for s in (live or {"sets": {}})["sets"].values() for r in s["rows"]})) or "n/a"
    out += [f"## Live model ({cfg})", ""]
    out += render_summary("Live model summary", live, True)
    out += ["### Failures and observations (latest live run)", ""] + render_failures(live) + [""]
    notes = EVAL / "live_notes.md"
    if live and notes.exists():
        out += [notes.read_text(encoding="utf-8").rstrip(), ""]
    out += ["## Per-PR results", ""] + render_rows("Live model", live) + render_rows("Mock baseline", mock)
    out += ["## Caveats", "",
            "- Tiny sets (10 synthetic + 5 real PRs): one PR moves a percentage by 10-20 points. These are "
            "regression-grade numbers, not a benchmark.",
            "- Real-PR labels are subjective; merged PRs are mostly good code, so the real set mainly tests false escalations "
            "and score sanity, not blocker recall.",
            "- Cost is computed from the token usage the API returns times the list price assumed in `app/core/llm_reviewer.py`; "
            "latency includes network time from the machine that ran the eval and varies run to run.",
            "- Free-tier rate limits (429) cause fallbacks to the second provider; those are counted above, not hidden.",
            "- `llama-3.3-70b-versatile` and `gemini-2.0-flash` were no longer served when this was run, so the live numbers "
            "are for the models named above, not for llama-3.3-70b.",
            "- Mentor-minutes saved are modelled (10 min manual vs 3 to skim an escalation / 1 to spot-check an auto-approve), not measured."]
    (EVAL / "results.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mock", action="store_true")
    g.add_argument("--live", action="store_true")
    args = ap.parse_args()
    has_key = bool(get_secret("GROQ_API_KEY") or get_secret("GEMINI_API_KEY"))
    live = args.live or (not args.mock and has_key)
    if live and not has_key:
        sys.exit("No GROQ_API_KEY / GEMINI_API_KEY found (env or .env); cannot run live.")
    if live:
        print(f"mode=live groq_key={bool(get_secret('GROQ_API_KEY'))} gemini_key={bool(get_secret('GEMINI_API_KEY'))} "
              f"github_token={bool(get_secret('GITHUB_TOKEN'))} models={llm_reviewer.GROQ_MODEL}, {llm_reviewer.GEMINI_MODEL}")
    else:
        print("mode=mock")
    data = {"date": date.today().isoformat(), "sets": {n: run_set(n, live) for n in ("synthetic", "real")}}
    (EVAL / ("live_results.json" if live else "mock_results.json")).write_text(json.dumps(data, indent=1), encoding="utf-8")
    render()
    for n, s in data["sets"].items():
        if s["rows"]:
            sm = summarize(s["rows"])
            print(f"{n}: triage {sm['tri_ok']}/{sm['n']}, seeded {sm['hit']}/{sm['seeded']}, "
                  f"false-esc {sm['clean_fp']}/{sm['clean_n']}, avg {sm['lat_avg']:.2f}s, "
                  f"${sm['cost_avg']:.5f}/PR, fallbacks {sm['fallbacks']}")


if __name__ == "__main__":
    main()
