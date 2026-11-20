import pytest
from fastapi.testclient import TestClient

from app.core.pipeline import Store, preload_samples
from api import server

from .test_static_checks import mk

VULN = mk("app/s.py", "import sqlite3", 'cur.execute(f"SELECT * FROM u WHERE n = {n}")')


@pytest.fixture()
def client(tmp_path, monkeypatch):
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "GITHUB_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    st = Store(tmp_path / "store.json")
    preload_samples(st)
    monkeypatch.setattr(server, "store", st)
    server._hits.clear()
    server._cache.clear()
    return TestClient(server.app)


def test_health_mock_mode(client):
    j = client.get("/api/health").json()
    assert j["status"] == "ok" and j["mode"] == "mock" and j["providers"] == []
    assert "Python Backend" in j["tracks"]


def test_review_pasted_diff_mock(client):
    r = client.post("/api/review", json={"diff": VULN, "track": "Python Backend",
                                         "week": "Weeks 5-6: Core architecture (auth, DB, APIs)"})
    assert r.status_code == 200
    j = r.json()
    assert j["final_triage"] == "BLOCKER" and j["meta"]["provider"] == "mock"
    assert any(f["rule"] == "sql-injection" for f in j["findings"])
    assert j["review"]["inline_comments"][0]["line"] == 2
    assert j["diff_files"][0]["lines"][1]["kind"] == "add"
    # appears in queue and stats
    ids = [q["id"] for q in client.get("/api/queue").json()]
    assert j["id"] in ids
    assert client.get("/api/stats").json()["total"] == 11


def test_review_sample_and_copy_flag(client):
    r = client.post("/api/review", json={"sample_id": "s08-lru-cache-copied", "track": "AI & Vector Intelligence",
                                         "week": "Weeks 3-4: Bug hunting & testing"})
    j = r.json()
    assert r.status_code == 200 and j["similarity_flag"] and j["similar_to"] == "s07-lru-cache-original"
    assert j["final_triage"] == "NEEDS_MENTOR"


@pytest.mark.parametrize("body,code", [
    ({}, 422),                                                        # nothing provided
    ({"diff": "hello world"}, 422),                                   # not a diff
    ({"pr_url": "https://example.com/nope"}, 422),                    # bad PR URL
    ({"diff": VULN, "track": "Nope"}, 422),                           # bad track
    ({"sample_id": "does-not-exist"}, 404),
    ({"diff": "x" * 400_000}, 413),
])
def test_review_errors(client, body, code):
    r = client.post("/api/review", json=body)
    assert r.status_code == code and r.json()["detail"]


def test_github_errors_are_mapped(client, monkeypatch):
    def boom(url):
        raise server.GitHubError("GitHub rate limit hit. Set GITHUB_TOKEN or paste the diff instead.")
    monkeypatch.setattr(server, "fetch_pr", boom)
    r = client.post("/api/review", json={"pr_url": "https://github.com/a/b/pull/1"})
    assert r.status_code == 429 and "rate limit" in r.json()["detail"].lower()


def test_queue_sorted_and_filter(client):
    q = client.get("/api/queue").json()
    assert len(q) == 10
    assert [x["priority"] for x in q] == sorted((x["priority"] for x in q), reverse=True)
    blockers = client.get("/api/queue", params={"triage": "BLOCKER"}).json()
    assert {x["triage"] for x in blockers} == {"BLOCKER"} and len(blockers) == 2


def test_stats(client):
    s = client.get("/api/stats").json()
    assert s["total"] == 10 and s["triage"] == {"AUTO_APPROVE": 3, "NEEDS_MENTOR": 5, "BLOCKER": 2}
    assert s["auto_approved_pct"] == 30.0 and s["hours_saved"] > 0 and s["copy_flags"] == 1


def test_samples_and_review_detail(client):
    assert len(client.get("/api/samples").json()) == 10
    d = client.get("/api/samples/s02-sqli-search").json()
    assert "diff --git" in d["diff"]
    assert client.get("/api/samples/nope").status_code == 404
    assert client.get("/api/reviews/s02-sqli-search").json()["final_triage"] == "BLOCKER"
    assert client.get("/api/reviews/nope").status_code == 404


def test_unknown_api_route_is_json_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.json()["detail"] == "Not found"


def test_store_is_seeded_when_file_missing(tmp_path):
    """Ephemeral hosts (Render) start without data/store.json: the 10 samples must be re-created on startup."""
    from app.core.pipeline import Store, load_samples, preload_samples
    s = Store(tmp_path / "missing" / "store.json")
    assert s.items == []
    preload_samples(s)
    assert len(s.items) == len(load_samples()) == 10
    assert all(x.meta.provider == "mock" for x in s.items)  # seeding never spends LLM quota


def test_groq_429_falls_back_to_gemini_without_retry(monkeypatch):
    from app.core import llm_reviewer as L
    calls = {"groq": 0, "gemini": 0}

    class R:
        ok = False
        status_code = 429
        text = "rate limited"
        headers = {"retry-after": "30"}

    def fake_post(url, **kw):
        calls["groq"] += 1
        return R()

    def fake_gemini(system, user, key, timeout=40):
        calls["gemini"] += 1
        import json
        return json.dumps({"scores": {"correctness": 4, "code_quality": 4, "security": 4, "testing": 4, "roadmap_alignment": 4},
                           "overall_score": 4.0, "summary": "Looks good overall.", "inline_comments": [], "triage": "AUTO_APPROVE"}), 10, 10

    monkeypatch.setenv("GROQ_API_KEY", "x"); monkeypatch.setenv("GEMINI_API_KEY", "y")
    monkeypatch.setattr(L.requests, "post", fake_post)
    monkeypatch.setattr(L, "_call_gemini", fake_gemini)
    import time
    from app.core.diff_parser import parse_diff
    t = time.time()
    res, meta = L.review_pr(parse_diff(VULN), [], "Python Backend", list(L.WEEKS)[0])
    assert meta.provider == "gemini", meta.fallback_errors
    assert calls == {"groq": 1, "gemini": 1} and time.time() - t < 2


def test_all_providers_fail_gives_labeled_demo_fallback(monkeypatch):
    from app.core import llm_reviewer as L
    from app.core.diff_parser import parse_diff

    def boom(*a, **k):
        raise L.requests.Timeout("slow")
    monkeypatch.setenv("GROQ_API_KEY", "x"); monkeypatch.setenv("GEMINI_API_KEY", "y")
    monkeypatch.setattr(L.requests, "post", boom); monkeypatch.setattr(L, "_call_gemini", boom)
    _, meta = L.review_pr(parse_diff(VULN), [], "Python Backend", list(L.WEEKS)[0])
    assert meta.provider == "mock" and meta.demo_fallback and len(meta.fallback_errors) == 2


def test_deadline_skips_providers(monkeypatch):
    from app.core import llm_reviewer as L
    from app.core.diff_parser import parse_diff
    monkeypatch.setenv("GROQ_API_KEY", "x"); monkeypatch.setattr(L, "REVIEW_DEADLINE_S", 0)
    _, meta = L.review_pr(parse_diff(VULN), [], "Python Backend", list(L.WEEKS)[0])
    assert meta.demo_fallback and "budget" in meta.fallback_errors[0]


def test_cache_returns_same_review_instantly(client, monkeypatch):
    body = {"diff": VULN, "track": "Python Backend", "week": "Weeks 5-6: Core architecture (auth, DB, APIs)"}
    a = client.post("/api/review", json=body).json()
    from app.core import pipeline
    monkeypatch.setattr(pipeline, "review_pr", lambda *x, **k: (_ for _ in ()).throw(AssertionError("not cached")))
    b = client.post("/api/review", json=body).json()
    assert a["id"] == b["id"]


def test_counts_include_llm_comments_and_pluralize(client):
    from app.core.llm_reviewer import InlineComment, ReviewResult, Scores
    from app.core.triage import decide, format_counts, severity_counts
    from app.core.static_checks import Finding
    sc = Scores(correctness=3, code_quality=3, security=3, testing=3, roadmap_alignment=3)
    cm = lambda sev: InlineComment(file="a.py", line=1, severity=sev, comment="Some comment", suggestion="")  # noqa: E731
    llm = ReviewResult(scores=sc, overall_score=3.0, summary="Summary text.", triage="NEEDS_MENTOR",
                       inline_comments=[cm("warning")] * 4 + [cm("info")] * 2)
    f = [Finding("todo", "warning", "t", "a.py", 1)]
    c = severity_counts(f, llm)
    assert c == {"critical": 0, "warning": 5, "info": 2}
    assert format_counts(c) == "0 critical · 5 warnings · 2 info"
    assert "1 warning ·" in format_counts({"critical": 0, "warning": 1, "info": 0})
    assert any("5 warnings" in r for r in decide(llm, f).reasons)


def test_cached_response_is_flagged(client):
    body = {"diff": VULN, "track": "Python Backend", "week": "Weeks 5-6: Core architecture (auth, DB, APIs)"}
    a = client.post("/api/review", json=body).json()
    b = client.post("/api/review", json=body).json()
    assert a["cached"] is False and b["cached"] is True and b["served_in_s"] < 1
    assert b["pipeline_latency_s"] == a["pipeline_latency_s"]  # original latency kept for the sub-line
    assert b["critical"] == a["critical"] >= 1 and "warnings" in b
    q = client.get("/api/queue").json()[0]
    assert {"critical", "warnings", "info"} <= q.keys()
