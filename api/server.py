"""FastAPI backend for BitReview AI. Wraps app/core and serves the built frontend.

Run:  uvicorn api.server:app --reload --port 8000
"""
from __future__ import annotations

import sys
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")  # local secrets (git-ignored); real env vars still win

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from app.core.diff_parser import parse_diff  # noqa: E402
from app.core.github import GitHubError, fetch_pr, parse_pr_url  # noqa: E402
from app.core.llm_reviewer import ReviewMeta, ReviewResult, get_secret  # noqa: E402
from app.core.pipeline import SAMPLES_DIR, Store, Submission, analyze, load_samples, preload_samples  # noqa: E402
from app.core.rubric import TRACKS, WEEKS  # noqa: E402
from app.core.similarity import DEFAULT_THRESHOLD  # noqa: E402

DIST = ROOT / "frontend" / "dist"
MAX_DIFF_BYTES = 300_000
RATE_LIMIT = 30           # reviews per IP per hour (protects LLM quota on a public demo)

app = FastAPI(title="BitReview AI API", version="1.0.0")
store = Store()
preload_samples(store)
_DIFFS: dict[str, str] = {}         # id -> raw diff for user-submitted reviews (in memory)
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


# ------------------------------------------------------------------ models
class ReviewRequest(BaseModel):
    pr_url: str | None = Field(None, description="Public GitHub PR URL")
    diff: str | None = Field(None, description="Unified diff text")
    sample_id: str | None = Field(None, description="Id of a bundled sample PR")
    track: str = TRACKS[0]
    week: str = list(WEEKS)[0]
    intern: str = "anonymous"
    title: str = ""
    commits: list[str] = []


class DiffLine(BaseModel):
    n: int | None
    kind: str  # add | del | ctx
    text: str


class DiffFile(BaseModel):
    path: str
    language: str
    lines: list[DiffLine]
    truncated: bool = False


class ReviewResponse(BaseModel):
    id: str
    intern: str
    track: str
    week: str
    title: str
    source: str
    created_at: str
    languages: list[str]
    n_files: int
    added: int
    removed: int
    review: ReviewResult
    meta: ReviewMeta
    findings: list[dict]
    similarity_top: float
    similar_to: str | None
    similarity_flag: bool
    final_triage: str
    priority: float
    reasons: list[str]
    minutes_saved: float
    pipeline_latency_s: float
    diff_files: list[DiffFile]


class QueueItem(BaseModel):
    id: str
    title: str
    intern: str
    track: str
    week: str
    source: str
    score: float
    triage: str
    priority: float
    critical: int
    warnings: int
    similarity_top: float
    similar_to: str | None
    similarity_flag: bool
    reasons: list[str]
    created_at: str


class Stats(BaseModel):
    total: int
    triage: dict[str, int]
    auto_approved_pct: float
    blockers: int
    copy_flags: int
    avg_score: float
    minutes_saved: float
    hours_saved: float
    avg_latency_s: float


class Health(BaseModel):
    status: str
    mode: str  # live | mock
    providers: list[str]
    github_token: bool
    tracks: list[str]
    weeks: list[str]


class SampleMeta(BaseModel):
    id: str
    title: str
    intern: str
    track: str
    week: str
    commits: list[str]


class SampleDetail(SampleMeta):
    diff: str


# ------------------------------------------------------------------ helpers
def _diff_files(diff_text: str, limit: int = 400) -> list[DiffFile]:
    out = []
    for f in parse_diff(diff_text).files:
        lines, truncated = [], False
        for h in f.hunks:
            for ln in h.lines:
                if len(lines) >= limit:
                    truncated = True
                    break
                lines.append(DiffLine(n=ln.new_no if ln.kind != "del" else ln.old_no, kind=ln.kind, text=ln.text))
        out.append(DiffFile(path=f.path, language=f.language, lines=lines, truncated=truncated))
    return out


def _diff_for(sub: Submission) -> str:
    if sub.id in _DIFFS:
        return _DIFFS[sub.id]
    p = SAMPLES_DIR / f"{sub.id}.diff"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _to_response(sub: Submission, flag_threshold: float = DEFAULT_THRESHOLD) -> ReviewResponse:
    d = sub.model_dump(exclude={"added_code", "commits"})
    return ReviewResponse(**d, similarity_flag=sub.similarity_top >= flag_threshold,
                          diff_files=_diff_files(_diff_for(sub)))


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    with _lock:
        q = _hits[ip]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            raise HTTPException(429, f"Rate limit reached ({RATE_LIMIT} reviews/hour). Try again later.")
        q.append(now)


# ------------------------------------------------------------------ routes
@app.get("/api/health", response_model=Health)
def health() -> Health:
    providers = [n for n, k in (("groq", "GROQ_API_KEY"), ("gemini", "GEMINI_API_KEY")) if get_secret(k)]
    return Health(status="ok", mode="live" if providers else "mock", providers=providers,
                  github_token=bool(get_secret("GITHUB_TOKEN")), tracks=TRACKS, weeks=list(WEEKS))


@app.post("/api/review", response_model=ReviewResponse)
def review(req: ReviewRequest, request: Request) -> ReviewResponse:
    if req.track not in TRACKS:
        raise HTTPException(422, f"Unknown track '{req.track}'. Choose one of: {', '.join(TRACKS)}.")
    if req.week not in WEEKS:
        raise HTTPException(422, f"Unknown roadmap stage '{req.week}'.")
    title, commits, intern, source, sub_id = req.title, req.commits, req.intern or "anonymous", "user", None
    diff_text = (req.diff or "").strip("\n")

    if req.sample_id:
        meta = next((m for m in load_samples() if m["id"] == req.sample_id), None)
        if not meta:
            raise HTTPException(404, f"Sample '{req.sample_id}' not found.")
        diff_text = (SAMPLES_DIR / f"{meta['id']}.diff").read_text(encoding="utf-8")
        title, commits, intern, source, sub_id = meta["title"], meta["commits"], meta["intern"], "sample", meta["id"]
    elif req.pr_url and req.pr_url.strip():
        try:
            parse_pr_url(req.pr_url)
        except GitHubError as e:
            raise HTTPException(422, str(e))
        _rate_limit(request)
        try:
            pr = fetch_pr(req.pr_url.strip())
        except GitHubError as e:
            msg = str(e)
            code = 429 if "rate limit" in msg.lower() else 404 if "not found" in msg.lower() else 502
            raise HTTPException(code, msg)
        diff_text, title, commits, intern, source = pr.diff, pr.title, pr.commits, pr.author or intern, "github"
    elif not diff_text:
        raise HTTPException(422, "Provide a PR URL, a diff, or a sample_id.")

    if len(diff_text.encode("utf-8")) > MAX_DIFF_BYTES:
        raise HTTPException(413, f"Diff too large (> {MAX_DIFF_BYTES // 1000} KB). Split the PR into smaller ones.")
    if not parse_diff(diff_text).files:
        raise HTTPException(422, "That does not look like a unified diff (no files found). Paste the output of `git diff`.")
    if source != "github" and not req.sample_id:
        _rate_limit(request)

    sub = analyze(diff_text, req.track, req.week, store, title=title, commits=commits, intern=intern,
                  source=source, sub_id=sub_id)
    if sub.source != "sample":
        _DIFFS[sub.id] = diff_text
    return _to_response(sub)


@app.get("/api/reviews/{sub_id}", response_model=ReviewResponse)
def get_review(sub_id: str) -> ReviewResponse:
    sub = next((s for s in store.items if s.id == sub_id), None)
    if not sub:
        raise HTTPException(404, f"Review '{sub_id}' not found.")
    return _to_response(sub)


@app.get("/api/queue", response_model=list[QueueItem])
def queue(triage: str | None = None) -> list[QueueItem]:
    items = sorted(store.items, key=lambda s: -s.priority)
    return [QueueItem(
        id=s.id, title=s.title, intern=s.intern, track=s.track, week=s.week, source=s.source,
        score=s.review.overall_score, triage=s.final_triage, priority=s.priority,
        critical=sum(f["severity"] == "critical" for f in s.findings),
        warnings=sum(f["severity"] == "warning" for f in s.findings),
        similarity_top=s.similarity_top, similar_to=s.similar_to,
        similarity_flag=s.similarity_top >= DEFAULT_THRESHOLD, reasons=s.reasons, created_at=s.created_at,
    ) for s in items if not triage or s.final_triage == triage]


@app.get("/api/stats", response_model=Stats)
def stats() -> Stats:
    items = store.items
    n = len(items)
    dist = {k: sum(s.final_triage == k for s in items) for k in ("AUTO_APPROVE", "NEEDS_MENTOR", "BLOCKER")}
    mins = sum(s.minutes_saved for s in items)
    return Stats(
        total=n, triage=dist, auto_approved_pct=round(100 * dist["AUTO_APPROVE"] / n, 1) if n else 0.0,
        blockers=dist["BLOCKER"], copy_flags=sum(s.similarity_top >= DEFAULT_THRESHOLD for s in items),
        avg_score=round(sum(s.review.overall_score for s in items) / n, 2) if n else 0.0,
        minutes_saved=round(mins, 1), hours_saved=round(mins / 60, 1),
        avg_latency_s=round(sum(s.pipeline_latency_s for s in items) / n, 3) if n else 0.0)


@app.get("/api/samples", response_model=list[SampleMeta])
def samples() -> list[SampleMeta]:
    return [SampleMeta(**{k: m[k] for k in ("id", "title", "intern", "track", "week", "commits")}) for m in load_samples()]


@app.get("/api/samples/{sample_id}", response_model=SampleDetail)
def sample(sample_id: str) -> SampleDetail:
    m = next((m for m in load_samples() if m["id"] == sample_id), None)
    if not m:
        raise HTTPException(404, f"Sample '{sample_id}' not found.")
    diff = (SAMPLES_DIR / f"{sample_id}.diff").read_text(encoding="utf-8")
    return SampleDetail(**{k: m[k] for k in ("id", "title", "intern", "track", "week", "commits")}, diff=diff)


@app.post("/api/reset")
def reset() -> dict:
    """Restore the demo data set (user submissions are removed)."""
    store.reset()
    _DIFFS.clear()
    preload_samples(store)
    return {"ok": True, "total": len(store.items)}


REPORTS = {"AI_Opportunity_Report.md": ROOT / "docs" / "AI_Opportunity_Report.md",
           "Technical_Approach.md": ROOT / "docs" / "Technical_Approach.md",
           "results.md": ROOT / "eval" / "results.md"}


@app.get("/reports/{name}", include_in_schema=False)
def report(name: str):
    path = REPORTS.get(name)
    if not path or not path.exists():
        raise HTTPException(404, "Report not found.")
    return FileResponse(path, media_type="text/markdown; charset=utf-8", content_disposition_type="inline")


# ------------------------------------------------------------------ frontend (SPA)
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    target = (DIST / full_path).resolve()
    if full_path and DIST in target.parents and target.is_file():
        return FileResponse(target)
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"detail": "Frontend not built. Run `npm run build` in frontend/ or use /docs for the API."},
                        status_code=404)
