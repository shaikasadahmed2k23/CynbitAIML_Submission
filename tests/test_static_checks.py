from app.core.diff_parser import parse_diff
from app.core.static_checks import run_static_checks


def mk(path: str, *lines: str) -> str:
    body = "\n".join("+" + l for l in lines)
    return f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"


def rules(diff: str, commits=None) -> set[str]:
    return {f.rule for f in run_static_checks(parse_diff(diff), commits)}


def test_hardcoded_secret_detected_with_line():
    d = mk("src/a.py", "import os", 'API_KEY = "sk-proj-FAKEFAKEFAKEFAKEFAKE0123456789"')
    f = [x for x in run_static_checks(parse_diff(d)) if x.rule == "hardcoded-secret"]
    assert f and f[0].line == 2 and f[0].severity == "critical"


def test_aws_key_and_env_usage():
    assert "hardcoded-secret" in rules(mk("a.py", 'k = "AKIAABCDEFGHIJKLMNOP"'))
    assert "hardcoded-secret" not in rules(mk("a.py", 'key = os.environ["API_KEY"]'))


def test_sql_injection():
    assert "sql-injection" in rules(mk("a.py", "cur.execute(f\"SELECT * FROM t WHERE n = '{n}'\")"))
    assert "sql-injection" not in rules(mk("a.py", 'cur.execute("SELECT * FROM t WHERE n = ?", (n,))'))


def test_debug_leftover_not_flagged_in_tests():
    assert "debug-leftover" in rules(mk("src/a.py", "print('x')"))
    assert "debug-leftover" not in rules(mk("tests/test_a.py", "print('x')"))


def test_missing_tests_vs_with_tests():
    src = mk("app/a.py", "x = 1")
    assert "missing-tests" in rules(src)
    assert "missing-tests" not in rules(src + mk("tests/test_a.py", "def test_a(): pass"))
    assert "missing-tests" not in rules(mk("README.md", "# hi"))


def test_n_plus_one_and_todo():
    code = mk("app/a.py", "for o in orders:", "    cur.execute('SELECT 1')", "# TODO fix")
    r = rules(code)
    assert "n-plus-one" in r and "todo" in r


def test_huge_pr_and_commit_messages():
    big = mk("app/big.py", *[f"x{i} = {i}" for i in range(600)])
    assert "huge-pr" in rules(big)
    r = rules(mk("app/a.py", "x = 1"), commits=["wip", "feat(api): add endpoint", "added stuff to the thing"])
    assert "bad-commit-message" in r and "non-conventional-commit" in r


def test_race_condition():
    code = mk("app/c.py", "import threading", "COUNTER = 0", "def inc():", "    global COUNTER", "    COUNTER += 1")
    assert "race-condition" in rules(code)
    locked = mk("app/c.py", "import threading", "LOCK = threading.Lock()", "COUNTER = 0", "def inc():", "    global COUNTER", "    COUNTER += 1")
    assert "race-condition" not in rules(locked)


def test_clean_diff_has_no_findings():
    d = mk("app/a.py", "def f(x):", "    return x + 1") + mk("tests/test_a.py", "def test_f(): assert True")
    assert rules(d, ["feat(core): add f"]) == set()
