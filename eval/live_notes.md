### Run history and variance (written by hand; the tables above are the latest run only)

Three live runs were made on 2026-11-20 against `openai/gpt-oss-120b` (Groq) with `gemini-2.5-flash` as fallback:

| Run | Prompt | Synthetic triage | Real triage | Mismatches |
|---|---|---|---|---|
| 1 (synthetic only) | original | 9/10 | not yet added | s09 (clean) escalated to NEEDS_MENTOR |
| 2 | original | 9/10 | 5/5 | s01 (clean) escalated: the LLM returned NEEDS_MENTOR on a tested, correct endpoint |
| 3 (tables above) | triage rules tightened (info-level nits must not trigger NEEDS_MENTOR) | 9/10 | 3/5 | s06 BLOCKER instead of NEEDS_MENTOR (model rated the race condition as critical); r02 escalated; r04 auto-approved by the Gemini fallback |

What this shows: the live reviewer found all 11 seeded issues in every run and never waved through a real blocker, but **its triage label is noisy on borderline PRs (about ±1 PR per set between runs)**, and the prompt tweak did not measurably fix that. I did not keep re-running until the numbers looked good. Most mismatches are the model being stricter than my labels (escalating, the safe direction); the one unsafe direction was r04, where the fallback model auto-approved a change I labeled as needing a mentor (a label I flagged as borderline beforehand).

Other failures seen: Groq's free tier returned HTTP 429 on 1-3 PRs per run (retried once, then the Gemini fallback answered, which is why those rows are slow); no JSON-parse failures, no schema-validation failures, and zero hallucinated line numbers (the guard dropped 0 comments in every run), so no parser fixes were needed. One real bug surfaced and was fixed: the triage reason said "clean; safe to auto-approve" even when the LLM itself had escalated.
