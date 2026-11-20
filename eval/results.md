# Evaluation results

Two reviewers are measured separately on the same labeled PRs. **The mock baseline is a rule-based reviewer (deterministic layers only); the live results use a real LLM and are the numbers to trust for model quality.** Regenerate with `python eval/run_eval.py --mock` and `python eval/run_eval.py --live`.

## Labeled sets

- **Synthetic (10 PRs):** hand-written in `data/build_samples.py` with seeded issues (11 in total), including one renamed copy. The mock heuristics were written by the same author, so mock detection here is optimistic by construction.
- **Real GitHub PRs:** merged public PRs pinned by URL in `data/build_eval_real.py` (diffs in `data/eval_real/`), labeled by me with the criteria in [`LABELING.md`](LABELING.md) before running any reviewer. Labels are one person's judgement, not ground truth, and the set is tiny.

## Mock baseline (rule-based, no LLM)

### Mock baseline summary

| Metric | Synthetic (10 seeded PRs) | Real GitHub PRs |
|---|---|---|
| PRs evaluated | 10 | 5 |
| Seeded-issue detection | 11/11 = 100% | not applicable (no seeded issues) |
| Triage accuracy | 10/10 = 100% | 3/5 = 60% |
| False escalations on AUTO_APPROVE-labeled PRs | 0/3 = 0% | 0/3 = 0% |
| Missed blockers | 0 | 0 |
| Latency avg / p50 / max (s per PR, whole pipeline) | 0.01 / 0.01 / 0.02 | 0.01 / 0.01 / 0.01 |
| Cost per PR (from token usage) | $0.00000 | $0.00000 |

_Run on 2026-11-20. Reviewer(s) actually used: mock/rule-based._

## Live model (gemini/gemini-2.5-flash, groq/openai/gpt-oss-120b)

### Live model summary

| Metric | Synthetic (10 seeded PRs) | Real GitHub PRs |
|---|---|---|
| PRs evaluated | 10 | 5 |
| Seeded-issue detection | 11/11 = 100% | not applicable (no seeded issues) |
| Triage accuracy | 9/10 = 90% | 3/5 = 60% |
| False escalations on AUTO_APPROVE-labeled PRs | 0/3 = 0% | 1/3 = 33% |
| Missed blockers | 0 | 0 |
| Latency avg / p50 / max (s per PR, whole pipeline) | 10.25 / 8.55 / 22.83 | 18.45 / 18.91 / 33.34 |
| Cost per PR (from token usage) | $0.00085 | $0.00107 |
| PRs that fell back to another provider / mock | 1 | 1 |
| Hallucinated comments dropped by the line guard | 0 | 0 |

_Run on 2026-11-20. Reviewer(s) actually used: gemini/gemini-2.5-flash, groq/openai/gpt-oss-120b._

### Failures and observations (latest live run)

- **s06-race-counter** (synthetic): triage BLOCKER instead of NEEDS_MENTOR. Reasons: 1 warning(s)
- **s08-lru-cache-copied** (synthetic): provider error → groq: HTTPError: 429 {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `
- **r02-requests-encode-files** (real): triage NEEDS_MENTOR instead of AUTO_APPROVE. Reasons: AI reviewer recommended a mentor look (no static findings)
- **r04-flask-context-order** (real): triage AUTO_APPROVE instead of NEEDS_MENTOR. Reasons: clean; safe to auto-approve; provider error → groq: HTTPError: 429 {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `

### Run history and variance (written by hand; the tables above are the latest run only)

Three live runs were made on 2026-11-20 against `openai/gpt-oss-120b` (Groq) with `gemini-2.5-flash` as fallback:

| Run | Prompt | Synthetic triage | Real triage | Mismatches |
|---|---|---|---|---|
| 1 (synthetic only) | original | 9/10 | not yet added | s09 (clean) escalated to NEEDS_MENTOR |
| 2 | original | 9/10 | 5/5 | s01 (clean) escalated: the LLM returned NEEDS_MENTOR on a tested, correct endpoint |
| 3 (tables above) | triage rules tightened (info-level nits must not trigger NEEDS_MENTOR) | 9/10 | 3/5 | s06 BLOCKER instead of NEEDS_MENTOR (model rated the race condition as critical); r02 escalated; r04 auto-approved by the Gemini fallback |

What this shows: the live reviewer found all 11 seeded issues in every run and never waved through a real blocker, but **its triage label is noisy on borderline PRs (about ±1 PR per set between runs)**, and the prompt tweak did not measurably fix that. I did not keep re-running until the numbers looked good. Most mismatches are the model being stricter than my labels (escalating, the safe direction); the one unsafe direction was r04, where the fallback model auto-approved a change I labeled as needing a mentor (a label I flagged as borderline beforehand).

Other failures seen: Groq's free tier returned HTTP 429 on 1-3 PRs per run (retried once, then the Gemini fallback answered, which is why those rows are slow); no JSON-parse failures, no schema-validation failures, and zero hallucinated line numbers (the guard dropped 0 comments in every run), so no parser fixes were needed. One real bug surfaced and was fixed: the triage reason said "clean; safe to auto-approve" even when the LLM itself had escalated.

## Per-PR results

### Live model

| Set | Sample | Seeded | Detected | Expected | Got | OK | Score | Latency (s) | Provider |
|---|---|---|---|---|---|---|---|---|---|
| synthetic | s01-clean-user-endpoint | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.4 | 3.29 | groq/openai/gpt-oss-120b |
| synthetic | s02-sqli-search | sql-injection, missing-tests | sql-injection✓, missing-tests✓ | BLOCKER | BLOCKER | ✓ | 1.6 | 3.77 | groq/openai/gpt-oss-120b |
| synthetic | s03-leaked-openai-key | hardcoded-secret, missing-tests | hardcoded-secret✓, missing-tests✓ | BLOCKER | BLOCKER | ✓ | 1.4 | 8.04 | groq/openai/gpt-oss-120b |
| synthetic | s04-no-tests-cart | missing-tests | missing-tests✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 3.8 | 16.29 | groq/openai/gpt-oss-120b |
| synthetic | s05-n-plus-one-report | n-plus-one | n-plus-one✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 3.6 | 12.72 | groq/openai/gpt-oss-120b |
| synthetic | s06-race-counter | race-condition | race-condition✓ | NEEDS_MENTOR | BLOCKER | ✗ | 2.8 | 8.55 | groq/openai/gpt-oss-120b |
| synthetic | s07-lru-cache-original | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.6 | 22.83 | groq/openai/gpt-oss-120b |
| synthetic | s08-lru-cache-copied | copied | copied✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.2 | 21.12 | gemini/gemini-2.5-flash |
| synthetic | s09-clean-react-filter | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.2 | 2.85 | groq/openai/gpt-oss-120b |
| synthetic | s10-debug-leftovers | debug-leftover, todo, bad-commit-message | debug-leftover✓, todo✓, bad-commit-message✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 2.8 | 3.03 | groq/openai/gpt-oss-120b |
| real | r01-requests-netrc-cve | (clean) | - | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 3.6 | 13.86 | groq/openai/gpt-oss-120b |
| real | r02-requests-encode-files | (clean) | - | AUTO_APPROVE | NEEDS_MENTOR | ✗ | 4.2 | 24.19 | groq/openai/gpt-oss-120b |
| real | r03-click-show-envvar | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 18.91 | groq/openai/gpt-oss-120b |
| real | r04-flask-context-order | (clean) | - | NEEDS_MENTOR | AUTO_APPROVE | ✗ | 4.8 | 33.34 | gemini/gemini-2.5-flash |
| real | r05-express-normalize-test | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 5.0 | 1.95 | groq/openai/gpt-oss-120b |

### Mock baseline

| Set | Sample | Seeded | Detected | Expected | Got | OK | Score | Latency (s) | Provider |
|---|---|---|---|---|---|---|---|---|---|
| synthetic | s01-clean-user-endpoint | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.00 | mock/rule-based |
| synthetic | s02-sqli-search | sql-injection, missing-tests | sql-injection✓, missing-tests✓ | BLOCKER | BLOCKER | ✓ | 3.6 | 0.01 | mock/rule-based |
| synthetic | s03-leaked-openai-key | hardcoded-secret, missing-tests | hardcoded-secret✓, missing-tests✓ | BLOCKER | BLOCKER | ✓ | 3.6 | 0.01 | mock/rule-based |
| synthetic | s04-no-tests-cart | missing-tests | missing-tests✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.2 | 0.01 | mock/rule-based |
| synthetic | s05-n-plus-one-report | n-plus-one | n-plus-one✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.2 | 0.01 | mock/rule-based |
| synthetic | s06-race-counter | race-condition | race-condition✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.4 | 0.01 | mock/rule-based |
| synthetic | s07-lru-cache-original | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.01 | mock/rule-based |
| synthetic | s08-lru-cache-copied | copied | copied✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.8 | 0.01 | mock/rule-based |
| synthetic | s09-clean-react-filter | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.01 | mock/rule-based |
| synthetic | s10-debug-leftovers | debug-leftover, todo, bad-commit-message | debug-leftover✓, todo✓, bad-commit-message✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.4 | 0.02 | mock/rule-based |
| real | r01-requests-netrc-cve | (clean) | - | NEEDS_MENTOR | AUTO_APPROVE | ✗ | 4.8 | 0.00 | mock/rule-based |
| real | r02-requests-encode-files | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.01 | mock/rule-based |
| real | r03-click-show-envvar | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.01 | mock/rule-based |
| real | r04-flask-context-order | (clean) | - | NEEDS_MENTOR | AUTO_APPROVE | ✗ | 4.8 | 0.01 | mock/rule-based |
| real | r05-express-normalize-test | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.01 | mock/rule-based |

## Caveats

- Tiny sets (10 synthetic + 5 real PRs): one PR moves a percentage by 10-20 points. These are regression-grade numbers, not a benchmark.
- Real-PR labels are subjective; merged PRs are mostly good code, so the real set mainly tests false escalations and score sanity, not blocker recall.
- Cost is computed from the token usage the API returns times the list price assumed in `app/core/llm_reviewer.py`; latency includes network time from the machine that ran the eval and varies run to run.
- Free-tier rate limits (429) cause fallbacks to the second provider; those are counted above, not hidden.
- `llama-3.3-70b-versatile` and `gemini-2.0-flash` were no longer served when this was run, so the live numbers are for the models named above, not for llama-3.3-70b.
- Mentor-minutes saved are modelled (10 min manual vs 3 to skim an escalation / 1 to spot-check an auto-approve), not measured.
