"""Evaluate the pipeline on the labeled samples and write eval/results.md.

Usage:
    python eval/run_eval.py            # uses live LLM if GROQ_API_KEY / GEMINI_API_KEY set, else mock
    python eval/run_eval.py --mock     # force deterministic mock
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.llm_reviewer import GROQ_PRICE, get_secret  # noqa: E402
from app.core.pipeline import SAMPLES_DIR, Store, analyze, load_samples  # noqa: E402
from app.core.similarity import DEFAULT_THRESHOLD  # noqa: E402


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    live = bool(get_secret("GROQ_API_KEY") or get_secret("GEMINI_API_KEY")) and not args.mock

    store = Store(Path(tempfile.mkdtemp()) / "eval_store.json")
    rows, seeded_total, seeded_hit, tri_ok = [], 0, 0, 0
    clean_fp = clean_n = 0
    lat, cost, proj = [], [], []
    for m in load_samples():
        diff = (SAMPLES_DIR / f"{m['id']}.diff").read_text(encoding="utf-8")
        sub = analyze(diff, m["track"], m["week"], store, title=m["title"], commits=m["commits"], intern=m["intern"],
                      source="sample", sub_id=m["id"], force_mock=not live)
        hits = {r: detected(r, sub) for r in m["seeded"]}
        seeded_total += len(hits)
        seeded_hit += sum(hits.values())
        ok = sub.final_triage == m["expected_triage"]
        tri_ok += ok
        if not m["seeded"]:
            clean_n += 1
            clean_fp += sub.final_triage != "AUTO_APPROVE"
        lat.append(sub.pipeline_latency_s)
        cost.append(sub.meta.cost_usd)
        proj.append((sub.meta.input_tokens * GROQ_PRICE[0] + sub.meta.output_tokens * GROQ_PRICE[1]) / 1e6)
        rows.append((m["id"], ", ".join(m["seeded"]) or "(clean)",
                     ", ".join(f"{r}{'✓' if h else '✗'}" for r, h in hits.items()) or "-",
                     m["expected_triage"], sub.final_triage, "✓" if ok else "✗",
                     sub.review.overall_score, sub.pipeline_latency_s))

    n = len(rows)
    provider = (sub.meta.provider + " / " + sub.meta.model) if live else "mock (rule-based, deterministic)"
    out = [
        "# Evaluation results", "",
        f"_Generated {date.today().isoformat()} by `python eval/run_eval.py{' --mock' if not live else ''}`._", "",
        f"- **Reviewer under test:** {provider}",
        f"- **Samples:** {n} labeled PRs ({clean_n} clean, {n - clean_n} with seeded issues; "
        f"{seeded_total} seeded issues in total)", "",
        "## Summary", "",
        "| Metric | Result |", "|---|---|",
        f"| Seeded-issue detection rate | **{seeded_hit}/{seeded_total} = {seeded_hit / seeded_total:.0%}** |",
        f"| Triage accuracy (final triage = label) | **{tri_ok}/{n} = {tri_ok / n:.0%}** |",
        f"| False-escalation rate on clean PRs | {clean_fp}/{clean_n} |",
        f"| Avg pipeline latency | {sum(lat) / n:.2f} s/PR |",
        f"| Avg measured LLM cost | ${sum(cost) / n:.5f} per PR |",
        f"| Projected cost on Groq llama-3.3-70b (token estimate) | ${sum(proj) / n:.5f} per PR "
        f"(≈ ${sum(proj) / n * 1000:.2f} per 1,000 PRs) |", "",
        "## Per-sample", "",
        "| Sample | Seeded issues | Detected | Expected | Got | OK | Score | Latency (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    out += [f"| {' | '.join(str(c) for c in r)} |" for r in rows]
    out += ["", "## Caveats", "",
            "- The sample set is small (10 PRs) and was written by the same author as the heuristics, so detection in "
            "mock mode is optimistic by construction. Treat it as a regression suite, not a benchmark.",
            "- Mock mode measures the static checks, similarity engine and triage logic. Run with a Groq key to "
            "measure the LLM reviewer; latency/cost rows then reflect real API calls.",
            "- Mentor-minutes saved are modelled (10 min manual vs 3 min to skim an escalation / 1 min to spot-check "
            "an auto-approve), not measured."]
    (ROOT / "eval" / "results.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:20]))


if __name__ == "__main__":
    main()
