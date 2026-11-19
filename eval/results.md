# Evaluation results

_Generated 2026-11-20 by `python eval/run_eval.py --mock`._

- **Reviewer under test:** mock (rule-based, deterministic)
- **Samples:** 10 labeled PRs (3 clean, 7 with seeded issues; 11 seeded issues in total)

## Summary

| Metric | Result |
|---|---|
| Seeded-issue detection rate | **11/11 = 100%** |
| Triage accuracy (final triage = label) | **10/10 = 100%** |
| False-escalation rate on clean PRs | 0/3 |
| Avg pipeline latency | 0.02 s/PR |
| Avg measured LLM cost | $0.00000 per PR |
| Projected cost on Groq llama-3.3-70b (token estimate) | $0.00073 per PR (≈ $0.73 per 1,000 PRs) |

## Per-sample

| Sample | Seeded issues | Detected | Expected | Got | OK | Score | Latency (s) |
|---|---|---|---|---|---|---|---|
| s01-clean-user-endpoint | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.003 |
| s02-sqli-search | sql-injection, missing-tests | sql-injection✓, missing-tests✓ | BLOCKER | BLOCKER | ✓ | 3.6 | 0.011 |
| s03-leaked-openai-key | hardcoded-secret, missing-tests | hardcoded-secret✓, missing-tests✓ | BLOCKER | BLOCKER | ✓ | 3.6 | 0.013 |
| s04-no-tests-cart | missing-tests | missing-tests✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.2 | 0.013 |
| s05-n-plus-one-report | n-plus-one | n-plus-one✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.2 | 0.013 |
| s06-race-counter | race-condition | race-condition✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.4 | 0.019 |
| s07-lru-cache-original | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.019 |
| s08-lru-cache-copied | copied | copied✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.8 | 0.022 |
| s09-clean-react-filter | (clean) | - | AUTO_APPROVE | AUTO_APPROVE | ✓ | 4.8 | 0.024 |
| s10-debug-leftovers | debug-leftover, todo, bad-commit-message | debug-leftover✓, todo✓, bad-commit-message✓ | NEEDS_MENTOR | NEEDS_MENTOR | ✓ | 4.4 | 0.028 |

## Caveats

- The sample set is small (10 PRs) and was written by the same author as the heuristics, so detection in mock mode is optimistic by construction. Treat it as a regression suite, not a benchmark.
- Mock mode measures the static checks, similarity engine and triage logic. Run with a Groq key to measure the LLM reviewer; latency/cost rows then reflect real API calls.
- Mentor-minutes saved are modelled (10 min manual vs 3 min to skim an escalation / 1 min to spot-check an auto-approve), not measured.
