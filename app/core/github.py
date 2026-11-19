"""Fetch a public PR's diff, title and commit messages via the GitHub REST API."""
from __future__ import annotations

import re
from dataclasses import dataclass

import requests

from .llm_reviewer import get_secret

PR_URL_RE = re.compile(r"github\.com/([\w.\-]+)/([\w.\-]+)/pull/(\d+)")


@dataclass
class PullRequest:
    diff: str
    title: str
    commits: list[str]
    author: str


class GitHubError(Exception):
    pass


def parse_pr_url(url: str) -> tuple[str, str, int]:
    m = PR_URL_RE.search(url or "")
    if not m:
        raise GitHubError("Not a valid GitHub PR URL (expected https://github.com/<owner>/<repo>/pull/<number>).")
    return m.group(1), m.group(2), int(m.group(3))


def fetch_pr(url: str, timeout: int = 20) -> PullRequest:
    owner, repo, num = parse_pr_url(url)
    base = f"https://api.github.com/repos/{owner}/{repo}/pulls/{num}"
    headers = {"X-GitHub-Api-Version": "2022-11-28", "User-Agent": "bitreview-ai"}
    if (tok := get_secret("GITHUB_TOKEN")):
        headers["Authorization"] = f"Bearer {tok}"
    try:
        meta = requests.get(base, headers={**headers, "Accept": "application/vnd.github+json"}, timeout=timeout)
        if meta.status_code == 404:
            raise GitHubError("PR not found (is the repo public?).")
        if meta.status_code in (403, 429):
            raise GitHubError("GitHub rate limit hit. Set GITHUB_TOKEN or paste the diff instead.")
        meta.raise_for_status()
        diff = requests.get(base, headers={**headers, "Accept": "application/vnd.github.v3.diff"}, timeout=timeout)
        diff.raise_for_status()
        commits = requests.get(base + "/commits?per_page=50", headers=headers, timeout=timeout)
        msgs = [c["commit"]["message"] for c in commits.json()] if commits.ok else []
    except requests.RequestException as e:
        raise GitHubError(f"Could not reach GitHub: {e}") from e
    j = meta.json()
    return PullRequest(diff=diff.text, title=j.get("title", ""), commits=msgs, author=(j.get("user") or {}).get("login", ""))
