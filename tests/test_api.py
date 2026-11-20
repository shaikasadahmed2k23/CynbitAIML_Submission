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
