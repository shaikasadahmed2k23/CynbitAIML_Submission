# Labeling criteria for the real-PR eval set

Labels were assigned by one person (the author) **before** running any reviewer on these PRs, from the diff and title only.
The PRs are merged public GitHub PRs, pinned by URL in `data/build_eval_real.py` (diffs stored in `data/eval_real/`).

| Label | Criteria |
|---|---|
| `AUTO_APPROVE` | One focused concern, under ~100 changed lines, behaviour changes come with tests (or the PR is test-only / docs-only), nothing security-sensitive. A mentor would merge after a glance. |
| `NEEDS_MENTOR` | Touches security-sensitive logic (credentials, parsing of untrusted input) or core framework semantics (request-context lifecycle, ordering), where a human should judge design and backward compatibility, even if tests exist. |
| `BLOCKER` | Contains a defect that must be fixed before merge (leaked secret, injection, data loss). None expected: these PRs were merged by maintainers, so this set cannot measure blocker recall (the synthetic set does). |

Known weakness: the boundary between the first two labels is a judgement call; flask#5797 in particular could reasonably be labeled `AUTO_APPROVE`.
