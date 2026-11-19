import json

import pytest
from pydantic import ValidationError

from app.core.diff_parser import parse_diff
from app.core.llm_reviewer import ReviewResult, _extract_json, mock_review, review_pr, sanitize_result
from app.core.static_checks import run_static_checks

from .test_static_checks import mk

VULN = mk("app/s.py", "import sqlite3", 'cur.execute(f"SELECT * FROM u WHERE n = {n}")')
WEEK = "Weeks 5-6: Core architecture (auth, DB, APIs)"


def _review(diff_text):
    p = parse_diff(diff_text)
    return p, review_pr(p, run_static_checks(p), "Python Backend", WEEK, force_mock=True)


def test_mock_output_validates_against_schema():
    _, (res, meta) = _review(VULN)
    ReviewResult.model_validate(json.loads(res.model_dump_json()))
    assert meta.provider == "mock" and res.triage == "BLOCKER" and res.scores.security <= 2
    assert res.inline_comments and res.inline_comments[0].line == 2


def test_mock_is_deterministic():
    _, (a, _) = _review(VULN)
    _, (b, _) = _review(VULN)
    assert a == b


def test_clean_diff_auto_approves():
    d = mk("app/a.py", "def f(x):", "    return x") + mk("tests/test_a.py", "def test_f(): pass")
    _, (res, _) = _review(d)
    assert res.triage == "AUTO_APPROVE" and res.overall_score >= 4


@pytest.mark.parametrize("bad", [
    {"scores": {"correctness": 9, "code_quality": 3, "security": 3, "testing": 3, "roadmap_alignment": 3},
     "overall_score": 3, "summary": "ok ok", "triage": "BLOCKER"},  # score > 5
    {"scores": {"correctness": 3, "code_quality": 3, "security": 3, "testing": 3, "roadmap_alignment": 3},
     "overall_score": 3, "summary": "ok ok", "triage": "MAYBE"},    # bad enum
    {"overall_score": 3, "summary": "ok ok", "triage": "BLOCKER"},  # missing scores
])
def test_invalid_json_rejected(bad):
    with pytest.raises(ValidationError):
        ReviewResult.model_validate(bad)


def test_extract_json_handles_markdown_fences():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('Here you go: {"a": 2} thanks') == {"a": 2}


def test_hallucinated_line_numbers_are_dropped():
    p = parse_diff(VULN)
    res = mock_review(p, run_static_checks(p), "t", "w")
    res.inline_comments[0].line = 999
    res.inline_comments.append(res.inline_comments[0].model_copy(update={"file": "ghost.py", "line": 1}))
    res, dropped = sanitize_result(res, p)
    assert dropped == 2 and res.inline_comments == []
