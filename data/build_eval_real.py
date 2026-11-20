"""Fetch the pinned real PRs into data/eval_real/ (diff + manifest). Needs network; GITHUB_TOKEN optional but advised.

Labels are assigned by hand using eval/LABELING.md. Re-running overwrites the .diff files with the same pinned PRs.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from app.core.github import fetch_pr  # noqa: E402

OUT = ROOT / "data" / "eval_real"
PY = "Python Backend"
W = "Weeks 5-6: Core architecture (auth, DB, APIs)"

# (id, url, track, expected_triage, label_note)
PRS = [
    ("r01-requests-netrc-cve", "https://github.com/psf/requests/pull/6963", PY, "NEEDS_MENTOR",
     "Security-sensitive: credential-leak fix in URL parsing; needs a human to judge."),
    ("r02-requests-encode-files", "https://github.com/psf/requests/pull/7502", PY, "AUTO_APPROVE",
     "Small focused bug fix with a regression test."),
    ("r03-click-show-envvar", "https://github.com/pallets/click/pull/3884", PY, "AUTO_APPROVE",
     "Focused bug fix with tests."),
    ("r04-flask-context-order", "https://github.com/pallets/flask/pull/5797", PY, "NEEDS_MENTOR",
     "Changes request-context push ordering (core semantics); design judgement needed."),
    ("r05-express-normalize-test", "https://github.com/expressjs/express/pull/6894", "Full Stack SaaS", "AUTO_APPROVE",
     "Test-only addition, tiny."),
]

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for pid, url, track, label, note in PRS:
        pr = fetch_pr(url)
        (OUT / f"{pid}.diff").write_text(pr.diff, encoding="utf-8")
        manifest.append({"id": pid, "url": url, "intern": pr.author or "unknown", "track": track, "week": W,
                         "title": pr.title, "commits": pr.commits, "expected_triage": label, "seeded": [],
                         "label_note": note})
        print(pid, len(pr.diff), "bytes;", pr.title)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
