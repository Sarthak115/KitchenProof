"""Scorer (deterministic): audit score, coverage, public score, tier and decay (§5.2, §6.4)."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..checks import CHECKS, SEVERITY_PENALTY
from ..timeutil import days_between

REVIEW_CONFIDENCE = 0.6
CRITICAL_CAP_CONFIDENCE = 0.8
CRITICAL_CAP = 40
MIN_COVERAGE = 0.7
PASS_SCORE = 60  # an audit "passed" for tier purposes
WINDOW_DAYS = 30


# ---------- per finding ----------


def gate_finding(f: dict) -> dict:
    """Set severity, needsReview and publicEligible on a finding (confidence gates + disputes)."""
    f = dict(f)
    f["severity"] = CHECKS[f["checkId"]].severity
    review = f.get("review") or {}
    decision = review.get("decision")
    conf = float(f.get("confidence") or 0)

    if decision == "overturned":
        f["effectiveStatus"] = "pass" if f["status"] == "fail" else f["status"]
        f["needsReview"] = False
        f["publicEligible"] = True
        return f
    if decision == "upheld":
        f["effectiveStatus"] = f["status"]
        f["needsReview"] = False
        f["publicEligible"] = True
        return f

    f["effectiveStatus"] = f["status"]
    needs_review = f["status"] != "not_verified" and conf < REVIEW_CONFIDENCE
    if f["status"] == "fail" and f["severity"] == "critical" and conf < CRITICAL_CAP_CONFIDENCE:
        needs_review = True
    f["needsReview"] = needs_review
    f["publicEligible"] = not needs_review and not f.get("disputed")
    return f


# ---------- per audit ----------


def score_audit(findings: list[dict], requested: int, integrity_verdict: str, trigger: str) -> dict:
    gated = [gate_finding(f) for f in findings]
    penalties = 0
    critical_cap = False
    verified = 0
    for f in gated:
        status = f["effectiveStatus"]
        if status == "not_verified" or f["needsReview"]:
            continue
        verified += 1  # disputed findings still count as shown, but carry no penalty
        if status == "fail" and f["publicEligible"]:
            penalties += SEVERITY_PENALTY[f["severity"]]
            upheld = (f.get("review") or {}).get("decision") == "upheld"
            if f["severity"] == "critical" and (upheld or float(f["confidence"]) >= CRITICAL_CAP_CONFIDENCE):
                critical_cap = True

    score = max(0, 100 - penalties)
    if critical_cap:
        score = min(score, CRITICAL_CAP)
    coverage = verified / requested if requested else 0.0

    if integrity_verdict == "failed":
        status, counted, score = "flagged", trigger != "practice", 0
    elif integrity_verdict == "suspicious":
        status, counted = "flagged", False
    elif coverage < MIN_COVERAGE:
        status, counted = "inconclusive", False
    else:
        status, counted = "scored", trigger != "practice"

    return {
        "findings": gated,
        "score": score,
        "coverage": round(coverage, 3),
        "status": status,
        "counted": counted,
        "issuesFound": sum(1 for f in gated if f["effectiveStatus"] == "fail" and f["publicEligible"]),
    }


# ---------- per restaurant ----------


def _weight(a: dict) -> float:
    return 1.5 if a.get("inspectorConfirmed") else 1.0


def _weighted(audits: list[dict]) -> int | None:
    if not audits:
        return None
    total = sum(_weight(a) for a in audits)
    return round(sum(a["score"] * _weight(a) for a in audits) / total)


def public_score(counted: list[dict], now: datetime) -> dict:
    """counted = non-practice audits with counted=True. Returns score + decay info."""
    if not counted:
        return {"publicScore": None, "lastCountedAuditAt": None, "decayed": False, "notRecentlyVerified": False}
    counted = sorted(counted, key=lambda a: a["completedAt"])
    last_at = counted[-1]["completedAt"]
    window_start = last_at - timedelta(days=WINDOW_DAYS)
    base = _weighted([a for a in counted if a["completedAt"] >= window_start])
    age = days_between(now, last_at)
    if age > 60:
        return {"publicScore": None, "lastCountedAuditAt": last_at, "decayed": True, "notRecentlyVerified": True}
    decay = 0
    if age > WINDOW_DAYS:
        decay = 5 * int((age - WINDOW_DAYS) // 7)
    return {
        "publicScore": max(0, base - decay),
        "lastCountedAuditAt": last_at,
        "decayed": decay > 0,
        "notRecentlyVerified": False,
    }


def tier(audits: list[dict], inspector_visit_at: datetime | None, now: datetime) -> str:
    recent = [a for a in audits if a.get("completedAt") and days_between(now, a["completedAt"]) <= WINDOW_DAYS]
    if any((a.get("integrity") or {}).get("verdict") == "failed" for a in recent):
        return "bronze"
    passed = [
        a
        for a in recent
        if a["trigger"] in ("surprise", "customer")
        and a.get("counted")
        and (a.get("integrity") or {}).get("verdict") == "clean"
        and (a.get("score") or 0) >= PASS_SCORE
    ]
    if len(passed) < 2:
        return "bronze"
    if inspector_visit_at and days_between(now, inspector_visit_at) <= 180:
        return "gold"
    return "silver"
