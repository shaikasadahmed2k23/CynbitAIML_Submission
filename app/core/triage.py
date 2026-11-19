"""Combine static + LLM + similarity into a mentor-queue priority score."""
from __future__ import annotations

from dataclasses import dataclass

from .llm_reviewer import ReviewResult
from .static_checks import Finding

REVIEW_MIN_NO_AI = 10      # assumed mentor minutes for a manual first-pass review
REVIEW_MIN_AFTER_AI = 3    # assumed minutes to skim an AI-reviewed escalation
REVIEW_MIN_AUTO = 1        # assumed minutes to spot-check an auto-approved PR


@dataclass
class TriageDecision:
    final_triage: str
    priority: float          # 0-100, higher = review first
    reasons: list[str]
    minutes_saved: float


def decide(llm: ReviewResult, findings: list[Finding], similarity_top: float = 0.0,
           similarity_threshold: float = 0.85) -> TriageDecision:
    crit = sum(f.severity == "critical" for f in findings)
    warn = sum(f.severity == "warning" for f in findings)
    reasons: list[str] = []
    triage = llm.triage

    # Safety rails: the LLM may not wave through what static checks flagged hard.
    if crit and triage != "BLOCKER":
        triage = "BLOCKER"
        reasons.append("static check found critical issue; escalated")
    copied = similarity_top >= similarity_threshold
    if copied:
        reasons.append(f"possible copied submission (similarity {similarity_top:.0%})")
        if triage == "AUTO_APPROVE":
            triage = "NEEDS_MENTOR"
    if triage == "AUTO_APPROVE" and warn >= 2:
        triage = "NEEDS_MENTOR"
        reasons.append("multiple static warnings; human check")

    priority = (5 - llm.overall_score) / 4 * 40 + min(crit, 3) * 15 + min(warn, 4) * 4
    priority += {"BLOCKER": 20, "NEEDS_MENTOR": 8, "AUTO_APPROVE": 0}[triage]
    if copied:
        priority += 15
    priority = round(min(100.0, priority), 1)
    if crit:
        reasons.append(f"{crit} critical finding(s)")
    if warn:
        reasons.append(f"{warn} warning(s)")
    if not reasons:
        reasons.append("clean; safe to auto-approve")

    after = REVIEW_MIN_AUTO if triage == "AUTO_APPROVE" else REVIEW_MIN_AFTER_AI
    return TriageDecision(triage, priority, reasons, REVIEW_MIN_NO_AI - after)
