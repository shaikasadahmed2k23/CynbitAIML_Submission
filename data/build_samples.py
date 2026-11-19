"""Generate realistic sample PR diffs + labels (manifest.json) into data/samples.

Run:  python data/build_samples.py
Every sample is a new-file-only unified diff, so line numbers are exact.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "samples"


def new_file_diff(path: str, content: str) -> str:
    lines = content.strip("\n").split("\n")
    body = "\n".join("+" + l for l in lines)
    return (f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n"
            f"@@ -0,0 +1,{len(lines)} @@\n{body}\n")


# ---------------------------------------------------------------- code bodies
CLEAN_API = '''
import sqlite3
from fastapi import FastAPI, HTTPException

app = FastAPI()
DB_PATH = "app.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


@app.get("/users/{user_id}")
def get_user(user_id: int):
    """Return a single user or 404."""
    with get_conn() as conn:
        row = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return {"id": row[0], "name": row[1], "email": row[2]}
'''
CLEAN_API_TEST = '''
from fastapi.testclient import TestClient
from app.users import app

client = TestClient(app)


def test_unknown_user_returns_404():
    assert client.get("/users/999999").status_code == 404


def test_sql_metacharacters_are_not_executed():
    assert client.get("/users/1;DROP TABLE users").status_code == 422
'''

SQLI_API = '''
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/search")
def search():
    name = request.args.get("name", "")
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute(f"SELECT id, name, email FROM users WHERE name = '{name}'")
    rows = cur.fetchall()
    return jsonify(rows)
'''

LEAKED_KEY = '''
const express = require("express");
const axios = require("axios");

const router = express.Router();
const OPENAI_API_KEY = "sk-proj-FAKEFAKEFAKEFAKEFAKE0123456789";

router.post("/summarize", async (req, res) => {
  const { text } = req.body;
  const r = await axios.post(
    "https://api.openai.com/v1/chat/completions",
    { model: "gpt-4o-mini", messages: [{ role: "user", content: `Summarize: ${text}` }] },
    { headers: { Authorization: `Bearer ${OPENAI_API_KEY}` } }
  );
  res.json({ summary: r.data.choices[0].message.content });
});

module.exports = router;
'''

NO_TESTS = '''
from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
    qty: int


def cart_total(items: list[Item], discount_pct: float = 0.0) -> float:
    subtotal = sum(i.price * i.qty for i in items)
    return round(subtotal * (1 - discount_pct / 100), 2)


def apply_coupon(total: float, code: str) -> float:
    coupons = {"SAVE10": 0.10, "SAVE20": 0.20}
    return round(total * (1 - coupons.get(code, 0)), 2)
'''

N_PLUS_ONE = '''
import sqlite3


def orders_report(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT id, customer_id, total FROM orders")
    report = []
    for order in cur.fetchall():
        c2 = conn.cursor()
        c2.execute("SELECT name FROM customers WHERE id = ?", (order[1],))
        customer = c2.fetchone()
        report.append({"order": order[0], "customer": customer[0], "total": order[2]})
    return report
'''
N_PLUS_ONE_TEST = '''
import sqlite3
from app.reports import orders_report


def test_orders_report_returns_customer_names():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (id INTEGER, name TEXT)")
    conn.execute("CREATE TABLE orders (id INTEGER, customer_id INTEGER, total REAL)")
    conn.execute("INSERT INTO customers VALUES (1, 'Asha')")
    conn.execute("INSERT INTO orders VALUES (10, 1, 99.5)")
    assert orders_report(conn)[0]["customer"] == "Asha"
'''

RACE = '''
import threading

COUNTER = 0


def increment_many(n: int) -> None:
    global COUNTER
    for _ in range(n):
        COUNTER += 1


def run(threads: int = 8, per_thread: int = 100_000) -> int:
    workers = [threading.Thread(target=increment_many, args=(per_thread,)) for _ in range(threads)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    return COUNTER
'''
RACE_TEST = '''
from app.counter import run


def test_run_counts_all_increments():
    assert run(threads=4, per_thread=1000) == 4000
'''


def lru(vars_: dict[str, str], comment_style: str) -> str:
    v = vars_
    return f'''
from collections import OrderedDict


class {v["cls"]}:
    {comment_style}
    def __init__(self, {v["cap"]}: int):
        if {v["cap"]} <= 0:
            raise ValueError("capacity must be positive")
        self.{v["cap"]} = {v["cap"]}
        self.{v["store"]} = OrderedDict()

    def get(self, {v["key"]}):
        if {v["key"]} not in self.{v["store"]}:
            return None
        self.{v["store"]}.move_to_end({v["key"]})
        return self.{v["store"]}[{v["key"]}]

    def put(self, {v["key"]}, {v["val"]}):
        self.{v["store"]}[{v["key"]}] = {v["val"]}
        self.{v["store"]}.move_to_end({v["key"]})
        if len(self.{v["store"]}) > self.{v["cap"]}:
            self.{v["store"]}.popitem(last=False)

    def __len__(self):
        return len(self.{v["store"]})
'''


LRU_A = lru(dict(cls="LRUCache", cap="capacity", store="data", key="key", val="value"), "# least-recently-used cache")
LRU_B = lru(dict(cls="Cache", cap="size", store="items", key="k", val="v"), "# simple eviction cache I wrote")
LRU_TEST_A = '''
import pytest
from app.cache import LRUCache


def test_evicts_least_recently_used():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1


def test_invalid_capacity():
    with pytest.raises(ValueError):
        LRUCache(0)
'''
LRU_TEST_B = LRU_TEST_A.replace("LRUCache", "Cache")

REACT_CLEAN = '''
import { useState } from "react";

export function StatusFilter({ statuses, onChange }) {
  const [active, setActive] = useState("all");

  const select = (s) => {
    setActive(s);
    onChange(s);
  };

  return (
    <div role="tablist" aria-label="Filter tickets by status">
      {["all", ...statuses].map((s) => (
        <button key={s} role="tab" aria-selected={active === s} onClick={() => select(s)}>
          {s}
        </button>
      ))}
    </div>
  );
}
'''
REACT_TEST = '''
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusFilter } from "./StatusFilter";

test("calls onChange with the selected status", () => {
  const onChange = jest.fn();
  render(<StatusFilter statuses={["open", "closed"]} onChange={onChange} />);
  fireEvent.click(screen.getByRole("tab", { name: "closed" }));
  expect(onChange).toHaveBeenCalledWith("closed");
});
'''

DEBUGGY = '''
const { login } = require("./auth");

// TODO: handle expired sessions
async function runLoginSuite(users) {
  for (const u of users) {
    console.log("trying", u.email);
    const res = await login(u.email, u.password);
    console.log(res);
    if (!res.ok) throw new Error("login failed for " + u.email);
  }
}

module.exports = { runLoginSuite };
'''
DEBUGGY_TEST = '''
const { runLoginSuite } = require("../src/loginSuite");

test("suite resolves for valid users", async () => {
  await expect(runLoginSuite([])).resolves.toBeUndefined();
});
'''

# ---------------------------------------------------------------- manifest
W12, W34, W56, W78, W910 = ("Weeks 1-2: Setup & git hygiene", "Weeks 3-4: Bug hunting & testing",
                            "Weeks 5-6: Core architecture (auth, DB, APIs)", "Weeks 7-8: Caching & concurrency",
                            "Weeks 9-10: Docker & CI/CD capstone")

SAMPLES = [
    dict(id="s01-clean-user-endpoint", intern="priya.sharma", track="Python Backend", week=W56,
         title="feat(api): add GET /users/{id} with tests", commits=["feat(api): add user lookup endpoint", "test(api): cover 404 and injection input"],
         files=[("app/users.py", CLEAN_API), ("tests/test_users.py", CLEAN_API_TEST)],
         expected_triage="AUTO_APPROVE", seeded=[]),
    dict(id="s02-sqli-search", intern="rohan.verma", track="Python Backend", week=W56,
         title="feat: add user search endpoint", commits=["feat: add search endpoint"],
         files=[("app/search.py", SQLI_API)],
         expected_triage="BLOCKER", seeded=["sql-injection", "missing-tests"]),
    dict(id="s03-leaked-openai-key", intern="ankit.joshi", track="Full Stack SaaS", week=W56,
         title="feat: summarize route using OpenAI", commits=["feat: summarize route", "fix"],
         files=[("server/routes/summarize.js", LEAKED_KEY)],
         expected_triage="BLOCKER", seeded=["hardcoded-secret", "missing-tests"]),
    dict(id="s04-no-tests-cart", intern="meera.nair", track="Python Backend", week=W34,
         title="feat: cart total and coupon helpers", commits=["feat(cart): add total + coupon helpers"],
         files=[("app/cart.py", NO_TESTS)],
         expected_triage="NEEDS_MENTOR", seeded=["missing-tests"]),
    dict(id="s05-n-plus-one-report", intern="karan.mehta", track="Python Backend", week=W78,
         title="feat(reports): orders report with customer names", commits=["feat(reports): orders report"],
         files=[("app/reports.py", N_PLUS_ONE), ("tests/test_reports.py", N_PLUS_ONE_TEST)],
         expected_triage="NEEDS_MENTOR", seeded=["n-plus-one"]),
    dict(id="s06-race-counter", intern="sneha.iyer", track="Python Backend", week=W78,
         title="feat: parallel counter with threads", commits=["feat: threaded counter"],
         files=[("app/counter.py", RACE), ("tests/test_counter.py", RACE_TEST)],
         expected_triage="NEEDS_MENTOR", seeded=["race-condition"]),
    dict(id="s07-lru-cache-original", intern="aditya.rao", track="AI & Vector Intelligence", week=W34,
         title="feat(cache): LRU cache with tests", commits=["feat(cache): add LRU cache", "test(cache): eviction + invalid capacity"],
         files=[("app/cache.py", LRU_A), ("tests/test_cache.py", LRU_TEST_A)],
         expected_triage="AUTO_APPROVE", seeded=[]),
    dict(id="s08-lru-cache-copied", intern="vikram.singh", track="AI & Vector Intelligence", week=W34,
         title="feat(cache): cache implementation", commits=["feat(cache): add cache with eviction", "test(cache): add tests"],
         files=[("app/cache.py", LRU_B), ("tests/test_cache.py", LRU_TEST_B)],
         expected_triage="NEEDS_MENTOR", seeded=["copied"], copy_of="s07-lru-cache-original"),
    dict(id="s09-clean-react-filter", intern="nisha.kapoor", track="Frontend Ops Dashboard", week=W56,
         title="feat(ui): accessible StatusFilter component", commits=["feat(ui): add StatusFilter with aria roles", "test(ui): onChange behaviour"],
         files=[("src/components/StatusFilter.jsx", REACT_CLEAN), ("src/components/StatusFilter.test.jsx", REACT_TEST)],
         expected_triage="AUTO_APPROVE", seeded=[]),
    dict(id="s10-debug-leftovers", intern="farhan.khan", track="QA & Test Automation", week=W34,
         title="test: login suite runner", commits=["wip", "fix"],
         files=[("src/loginSuite.js", DEBUGGY), ("tests/loginSuite.test.js", DEBUGGY_TEST)],
         expected_triage="NEEDS_MENTOR", seeded=["debug-leftover", "todo", "bad-commit-message"]),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for s in SAMPLES:
        diff = "".join(new_file_diff(p, c) for p, c in s.pop("files"))
        (OUT / f"{s['id']}.diff").write_text(diff, encoding="utf-8")
        manifest.append(s)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(manifest)} samples to {OUT}")


if __name__ == "__main__":
    main()
