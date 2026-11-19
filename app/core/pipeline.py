"""End-to-end pipeline + persistent submission store (JSON file)."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from .diff_parser import parse_diff
from .llm_reviewer import ReviewMeta, ReviewResult, review_pr
from .similarity import DEFAULT_THRESHOLD, find_similar
from .static_checks import run_static_checks
from .triage import decide

ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = ROOT / "data" / "samples"
STORE_PATH = ROOT / "data" / "store.json"


class Submission(BaseModel):
    id: str
    intern: str
    track: str
    week: str
    title: str
    commits: list[str] = []
    source: str = "user"  # sample | user | github
    created_at: str
    languages: list[str] = []
    n_files: int = 0
    added: int = 0
    removed: int = 0
    added_code: str = ""
    findings: list[dict] = []
    review: ReviewResult
    meta: ReviewMeta
    similarity_top: float = 0.0
    similar_to: str | None = None
    final_triage: str
    priority: float
    reasons: list[str] = []
    minutes_saved: float = 0.0
    pipeline_latency_s: float = 0.0


class Store:
    def __init__(self, path: Path = STORE_PATH):
        self.path = path
        self.items: list[Submission] = []
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self.items = [Submission.model_validate(x) for x in json.loads(self.path.read_text(encoding="utf-8"))]
            except Exception:
                self.items = []

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps([s.model_dump() for s in self.items], indent=1), encoding="utf-8")
        except OSError:
            pass  # read-only FS (some hosts): store stays in memory

    def code_map(self, exclude_id: str | None = None) -> dict[str, str]:
        return {s.id: s.added_code for s in self.items if s.id != exclude_id}

    def add(self, s: Submission) -> None:
        self.items = [x for x in self.items if x.id != s.id] + [s]
        self.save()

    def reset(self) -> None:
        self.items = []
        self.save()


def analyze(diff_text: str, track: str, week: str, store: Store, *, title: str = "", commits: list[str] | None = None,
            intern: str = "anonymous", source: str = "user", sub_id: str | None = None,
            force_mock: bool = False, threshold: float = DEFAULT_THRESHOLD, persist: bool = True) -> Submission:
    t0 = time.perf_counter()
    commits = commits or []
    sid = sub_id or f"pr-{uuid.uuid4().hex[:8]}"
    parsed = parse_diff(diff_text)
    findings = run_static_checks(parsed, commits)
    code = parsed.added_code()
    matches = find_similar(code, store.code_map(exclude_id=sid), threshold)
    top = matches[0] if matches else None
    review, meta = review_pr(parsed, findings, track, week, title, commits, force_mock=force_mock)
    decision = decide(review, findings, top.score if top else 0.0, threshold)
    sub = Submission(
        id=sid, intern=intern, track=track, week=week, title=title or sid, commits=commits, source=source,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        languages=parsed.languages, n_files=len(parsed.files), added=parsed.added_lines, removed=parsed.removed_lines,
        added_code=code, findings=[f.to_dict() for f in findings], review=review, meta=meta,
        similarity_top=round(top.score, 3) if top else 0.0, similar_to=top.other_id if top else None,
        final_triage=decision.final_triage, priority=decision.priority, reasons=decision.reasons,
        minutes_saved=decision.minutes_saved, pipeline_latency_s=round(time.perf_counter() - t0, 3),
    )
    if persist:
        store.add(sub)
    return sub


def load_samples() -> list[dict]:
    return json.loads((SAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))


def preload_samples(store: Store) -> None:
    """Populate an empty store with the labeled samples (mock mode, so it is instant and free)."""
    if store.items:
        return
    for m in load_samples():
        diff = (SAMPLES_DIR / f"{m['id']}.diff").read_text(encoding="utf-8")
        analyze(diff, m["track"], m["week"], store, title=m["title"], commits=m["commits"], intern=m["intern"],
                source="sample", sub_id=m["id"], force_mock=True)
