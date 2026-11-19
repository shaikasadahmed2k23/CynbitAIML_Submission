import type { ReviewResponse } from "./types";

/** Turns findings into a short, concrete to-do list for the intern. */
export function nextSteps(r: ReviewResponse): string[] {
  const rules = new Set(r.findings.map((f) => f.rule));
  const s: string[] = [];
  if (rules.has("hardcoded-secret")) s.push("Rotate the exposed credential now, move it to an environment variable, and remove it from git history.");
  if (rules.has("sql-injection")) s.push("Replace string-built SQL with parameterized queries.");
  if (rules.has("missing-tests")) s.push("Add tests for the changed source files: one happy path and one failure case.");
  if (rules.has("n-plus-one")) s.push("Batch the queries that run inside a loop into one JOIN or IN query.");
  if (rules.has("race-condition")) s.push("Protect shared state with a lock or use a thread-safe structure.");
  if (rules.has("debug-leftover") || rules.has("todo")) s.push("Remove debug prints and resolve or ticket the TODOs.");
  if (rules.has("bad-commit-message") || rules.has("non-conventional-commit"))
    s.push("Rewrite commit messages in conventional style, e.g. feat(api): add user lookup endpoint.");
  if (rules.has("huge-pr")) s.push("Split this PR into smaller, focused PRs.");
  if (r.similarity_flag) s.push(`Your code is very similar to ${r.similar_to}. Be ready to explain your own approach to your mentor.`);
  if (!s.length) s.push("Nothing blocking. Keep PRs small and tested; a mentor will spot-check.");
  return s;
}
