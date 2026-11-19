"""BitReview AI - Streamlit app.  Run: streamlit run app/main.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.core.github import GitHubError, fetch_pr
from app.core.llm_reviewer import get_secret
from app.core.pipeline import Store, Submission, analyze, load_samples, preload_samples, SAMPLES_DIR
from app.core.rubric import TRACKS, WEEKS
from app.core.similarity import DEFAULT_THRESHOLD

st.set_page_config(page_title="BitReview AI", page_icon="🔍", layout="wide")

BADGE = {"AUTO_APPROVE": "🟢 AUTO_APPROVE", "NEEDS_MENTOR": "🟡 NEEDS_MENTOR", "BLOCKER": "🔴 BLOCKER"}
SEV_ICON = {"critical": "🔴", "warning": "🟠", "info": "🔵"}


@st.cache_resource
def get_store() -> Store:
    store = Store()
    preload_samples(store)
    return store


store = get_store()
live = bool(get_secret("GROQ_API_KEY") or get_secret("GEMINI_API_KEY"))

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.title("🔍 BitReview AI")
    st.caption("AI first-pass PR review + mentor triage for BitElevate")
    if live:
        st.success("LLM mode: live (Groq, Gemini fallback)")
    else:
        st.info("LLM mode: **MOCK** (no API key set). Static checks, similarity and triage are real; "
                "the rubric review is rule-based.")
    threshold = st.slider("Copy-detection threshold", 0.5, 1.0, DEFAULT_THRESHOLD, 0.01)
    force_mock = st.checkbox("Force mock mode", value=False, disabled=not live)
    if st.button("Reset to sample data"):
        store.reset()
        preload_samples(store)
        st.rerun()


def radar(sub: Submission) -> go.Figure:
    s = sub.review.scores.model_dump()
    labels = [k.replace("_", " ").title() for k in s]
    fig = go.Figure(go.Scatterpolar(r=list(s.values()) + [list(s.values())[0]], theta=labels + [labels[0]], fill="toself"))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5], tickvals=[1, 2, 3, 4, 5])), showlegend=False,
                      margin=dict(l=30, r=30, t=20, b=20), height=320)
    return fig


def next_steps(sub: Submission) -> list[str]:
    steps = []
    rules = {f["rule"] for f in sub.findings}
    if "hardcoded-secret" in rules:
        steps.append("**Rotate the leaked credential now**, move it to an environment variable and purge it from git history.")
    if "sql-injection" in rules:
        steps.append("Replace string-built SQL with parameterized queries.")
    if "missing-tests" in rules:
        steps.append("Add tests for the changed source files (happy path + one failure case).")
    if "n-plus-one" in rules:
        steps.append("Batch the in-loop queries into a single JOIN / IN query.")
    if "race-condition" in rules:
        steps.append("Protect shared state with a lock (or use a thread-safe structure).")
    if rules & {"debug-leftover", "todo"}:
        steps.append("Remove debug prints and resolve or ticket TODOs.")
    if rules & {"bad-commit-message", "non-conventional-commit"}:
        steps.append("Use conventional commits, e.g. `feat(api): add user lookup endpoint`.")
    if sub.similarity_top >= DEFAULT_THRESHOLD:
        steps.append(f"Your code is very similar to `{sub.similar_to}`. Be ready to explain your own approach to your mentor.")
    if not steps:
        steps.append("Nice work. Keep PRs small and tested; a mentor will spot-check.")
    return steps


def render_result(sub: Submission, key: str) -> None:
    c = st.columns(5)
    c[0].metric("Overall", f"{sub.review.overall_score}/5")
    c[1].metric("Triage", BADGE[sub.final_triage].split(" ", 1)[1])
    c[2].metric("Priority", sub.priority)
    c[3].metric("Similarity", f"{sub.similarity_top:.0%}")
    c[4].metric("Mentor min saved", sub.minutes_saved)
    st.markdown(f"**{BADGE[sub.final_triage]}**  ·  {sub.review.summary}")
    if sub.similarity_top >= threshold:
        st.warning(f"⚠️ Possible copy of **{sub.similar_to}** (similarity {sub.similarity_top:.0%}).")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Rubric")
        st.plotly_chart(radar(sub), width="stretch", key=f"radar-{key}-{sub.id}")
    with right:
        st.subheader("Scores")
        for k, v in sub.review.scores.model_dump().items():
            st.progress(v / 5, text=f"{k.replace('_', ' ').title()}: {v}/5")

    st.subheader("Inline comments")
    if sub.review.inline_comments:
        df = pd.DataFrame([{"": SEV_ICON[c.severity], "File": c.file, "Line": c.line, "Severity": c.severity,
                            "Comment": c.comment, "Suggestion": c.suggestion} for c in sub.review.inline_comments])
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.caption("No inline comments.")

    st.subheader("Actionable next steps")
    for s in next_steps(sub):
        st.markdown(f"- {s}")

    with st.expander("Static findings, reasons & run metadata"):
        st.write("**Triage reasons:**", "; ".join(sub.reasons))
        if sub.findings:
            st.dataframe(pd.DataFrame(sub.findings), width="stretch", hide_index=True)
        m = sub.meta
        st.caption(f"Provider: {m.provider} ({m.model}) · latency {m.latency_s}s · tokens {m.input_tokens}/{m.output_tokens} · "
                   f"est. cost ${m.cost_usd:.5f} · hallucinated comments dropped: {m.dropped_comments}")
        if m.fallback_errors:
            st.caption("Provider errors (fell back): " + " | ".join(m.fallback_errors))


tab_intern, tab_mentor = st.tabs(["🎓 Intern view", "🧑‍🏫 Mentor dashboard"])

# ------------------------------------------------------------------ intern
with tab_intern:
    st.header("Submit your PR for instant feedback")
    c1, c2, c3 = st.columns([2, 1, 1])
    intern = c1.text_input("Your name / handle", "new.intern")
    track = c2.selectbox("Track", TRACKS)
    week = c3.selectbox("Roadmap stage", list(WEEKS))

    sample_ids = ["—"] + [m["id"] for m in load_samples()]
    mode = st.radio("Input", ["GitHub PR URL", "Paste diff", "Load a sample"], horizontal=True)
    diff_text, title, commits, source = "", "", [], "user"
    if mode == "GitHub PR URL":
        url = st.text_input("Public PR URL", placeholder="https://github.com/owner/repo/pull/123")
        if url:
            source = "github"
    elif mode == "Paste diff":
        diff_text = st.text_area("Unified diff (git diff output)", height=220)
        title = st.text_input("PR title (optional)")
        commits = [c for c in st.text_area("Commit messages, one per line (optional)").splitlines() if c.strip()]
    else:
        pick = st.selectbox("Sample", sample_ids)
        if pick != "—":
            diff_text = (SAMPLES_DIR / f"{pick}.diff").read_text(encoding="utf-8")
            meta = next(m for m in load_samples() if m["id"] == pick)
            title, commits = meta["title"], meta["commits"]
            st.code(diff_text[:2500], language="diff")

    if st.button("Review my PR", type="primary"):
        try:
            if mode == "GitHub PR URL":
                with st.spinner("Fetching PR from GitHub…"):
                    pr = fetch_pr(url)
                diff_text, title, commits = pr.diff, pr.title, pr.commits
                intern = pr.author or intern
            if not diff_text.strip():
                st.error("Provide a PR URL, a diff, or pick a sample.")
            else:
                with st.spinner("Reviewing…"):
                    st.session_state["last"] = analyze(diff_text, track, week, store, title=title, commits=commits,
                                                       intern=intern, source=source, force_mock=force_mock, threshold=threshold)
        except GitHubError as e:
            st.error(str(e))
    if (last := st.session_state.get("last")):
        st.divider()
        st.caption(f"Submission `{last.id}` · {last.n_files} files · +{last.added}/-{last.removed} · {', '.join(last.languages) or 'n/a'}")
        render_result(last, "intern")

# ------------------------------------------------------------------ mentor
with tab_mentor:
    st.header("Mentor review queue")
    items = sorted(store.items, key=lambda s: -s.priority)
    n = len(items)
    counts = {k: sum(s.final_triage == k for s in items) for k in BADGE}
    saved = sum(s.minutes_saved for s in items)
    k = st.columns(5)
    k[0].metric("PRs reviewed", n)
    k[1].metric("🔴 Blockers", counts["BLOCKER"])
    k[2].metric("🟡 Needs mentor", counts["NEEDS_MENTOR"])
    k[3].metric("🟢 Auto-approve", counts["AUTO_APPROVE"])
    k[4].metric("Est. mentor-min saved", f"{saved:.0f}", help="Assumes 10 min manual review vs 3 min to skim an escalation / 1 min to spot-check an auto-approve.")
    st.caption(f"≈ {saved / 60:.1f} mentor-hours saved on {n} PRs ({saved / max(n, 1):.1f} min/PR)")

    flt = st.multiselect("Filter triage", list(BADGE), default=list(BADGE))
    rows = [{"Priority": s.priority, "Triage": BADGE[s.final_triage], "PR": s.id, "Intern": s.intern, "Track": s.track,
             "Score": s.review.overall_score, "Critical": sum(f["severity"] == "critical" for f in s.findings),
             "Warnings": sum(f["severity"] == "warning" for f in s.findings),
             "Copy flag": f"⚠️ {s.similarity_top:.0%} ~ {s.similar_to}" if s.similarity_top >= threshold else "",
             "Why": "; ".join(s.reasons)} for s in items if s.final_triage in flt]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    ids = [s.id for s in items if s.final_triage in flt]
    if ids:
        pick = st.selectbox("Open a PR", ids)
        sub = next(s for s in items if s.id == pick)
        st.markdown(f"**{sub.title}** by `{sub.intern}` · {sub.track} · {sub.week}")
        render_result(sub, "mentor")
