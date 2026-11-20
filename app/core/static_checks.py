"""Fast heuristic checks that run before (and independently of) the LLM."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .diff_parser import ParsedDiff

SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Groq/OpenAI-style key", re.compile(r"\b(?:sk|gsk)[-_][A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("Hardcoded credential", re.compile(r"""(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*["'][^"'\s]{8,}["']""")),
]
SQLI = re.compile(r"""(?i)(?:execute|query|cursor\.execute)\s*\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\+|\.format))""")
SQLI_FSTRING = re.compile(r"""(?i)f["'][^"']*\b(?:select|insert|update|delete)\b[^"']*\{""")
DEBUG_PATTERNS = [re.compile(r"^\s*print\("), re.compile(r"\bconsole\.log\("), re.compile(r"\bdebugger\b"), re.compile(r"\bpdb\.set_trace\(")]
TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
BAD_COMMIT_RE = re.compile(r"(?i)^(wip|fix|update|changes?|stuff|asdf+|test|commit|final|done|\.+)\s*\d*$")
CONVENTIONAL_RE = re.compile(r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)(\([\w\-/]+\))?!?: .{3,}")
LOOP_QUERY_RE = re.compile(r"(?i)for\s+.+\s+in\s+.+:\s*$")
BIG_PR_LINES = 500

TEST_PATH_RE = re.compile(r"(?i)(^|/)(tests?|__tests__|spec)(/|$)|(^|/)test_[^/]+\.py$|_test\.(py|go)$|\.(test|spec)\.(js|jsx|ts|tsx)$")
NON_SOURCE_EXT = (".md", ".yml", ".yaml", ".json", ".toml", ".txt", ".css", ".html", ".lock", ".cfg", ".ini", ".gitignore")


@dataclass
class Finding:
    rule: str
    severity: str  # info | warning | critical
    message: str
    file: str = ""
    line: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def is_test_file(path: str) -> bool:
    return bool(TEST_PATH_RE.search(path))


def is_source_file(path: str) -> bool:
    return not is_test_file(path) and not path.lower().endswith(NON_SOURCE_EXT) and "." in path.rsplit("/", 1)[-1]


def run_static_checks(diff: ParsedDiff, commit_messages: list[str] | None = None) -> list[Finding]:
    out: list[Finding] = []
    for f in diff.files:
        in_loop_indent: int | None = None
        for ln in f.added:
            t = ln.text
            for name, pat in SECRET_PATTERNS:
                if pat.search(t):
                    out.append(Finding("hardcoded-secret", "critical", f"Possible {name} committed in source.", f.path, ln.new_no))
                    break
            if SQLI.search(t) or SQLI_FSTRING.search(t):
                out.append(Finding("sql-injection", "critical", "SQL built via string formatting; use parameterized queries.", f.path, ln.new_no))
            if f.language in ("Python", "JavaScript", "TypeScript") and not is_test_file(f.path):
                if any(p.search(t) for p in DEBUG_PATTERNS):
                    out.append(Finding("debug-leftover", "warning", "Debug print/console.log left in code.", f.path, ln.new_no))
            if TODO_RE.search(t):
                out.append(Finding("todo", "info", "TODO/FIXME left in submitted code.", f.path, ln.new_no))
            # naive N+1 heuristic: query call inside a for-loop body
            if LOOP_QUERY_RE.search(t):
                in_loop_indent = len(t) - len(t.lstrip())
            elif in_loop_indent is not None:
                indent = len(t) - len(t.lstrip())
                if t.strip() and indent <= in_loop_indent:
                    in_loop_indent = None
                elif re.search(r"(?i)\.(execute|query|filter|find_one|fetchone|fetchall)\(|requests\.(get|post)\(|SELECT\s", t):
                    out.append(Finding("n-plus-one", "warning", "Query/IO call inside a loop; likely N+1 — batch or prefetch.", f.path, ln.new_no))
                    in_loop_indent = None

    # naive race-condition heuristic: threads + mutation of module-level state with no lock
    for f in diff.files:
        body = "\n".join(l.text for l in f.added)
        if re.search(r"Thread\(|ThreadPoolExecutor|threading", body) and not re.search(r"Lock|RLock|Semaphore|atomic|Queue", body):
            for ln in f.added:
                if re.match(r"\s*global\s+\w+", ln.text) or re.search(r"\b[A-Z_]{3,}\s*(\+|-)=\s*", ln.text):
                    out.append(Finding("race-condition", "warning",
                                       "Shared state mutated from threads without a lock; possible race condition.", f.path, ln.new_no))
                    break

    src = [f for f in diff.files if is_source_file(f.path) and not f.is_deleted and f.added]
    has_tests = any(is_test_file(f.path) and f.added for f in diff.files)
    if src and not has_tests:
        out.append(Finding("missing-tests", "warning", f"{len(src)} source file{'' if len(src) == 1 else 's'} changed but no tests added/updated.", src[0].path))

    total = diff.added_lines + diff.removed_lines
    if total > BIG_PR_LINES:
        out.append(Finding("huge-pr", "warning", f"PR changes {total} lines (> {BIG_PR_LINES}); split into smaller PRs."))

    for msg in commit_messages or []:
        first = msg.strip().splitlines()[0] if msg.strip() else ""
        if BAD_COMMIT_RE.match(first) or len(first) < 5:
            out.append(Finding("bad-commit-message", "info", f"Uninformative commit message: '{first}'."))
        elif not CONVENTIONAL_RE.match(first):
            out.append(Finding("non-conventional-commit", "info", f"Commit message not in conventional-commit style: '{first[:60]}'."))
    return out
