"""Inspector risk ranking (deterministic, with plain-language reasons) (§6.5)."""

from __future__ import annotations


def compute(
    *,
    public_score: int | None,
    missed_checks_30d: int,
    integrity_issue_30d: bool,
    open_disputes: int,
    score_drop: int | None,
    no_counted_audit_30d: bool,
) -> tuple[int, list[str]]:
    terms: list[tuple[float, str]] = []

    score_for_risk = public_score if public_score is not None else 50
    base = (100 - score_for_risk) * 0.5
    if public_score is None:
        terms.append((base, "No verified Kitchen Score"))
    elif base >= 10:
        terms.append((base, f"Kitchen Score is {public_score}"))
    else:
        terms.append((base, ""))

    if missed_checks_30d:
        s = "" if missed_checks_30d == 1 else "s"
        terms.append((15 * missed_checks_30d, f"{missed_checks_30d} missed check{s} this month"))
    if integrity_issue_30d:
        terms.append((20, "Audit flagged for possible staging or failed verification"))
    if open_disputes:
        s = "" if open_disputes == 1 else "s"
        terms.append((10 * open_disputes, f"{open_disputes} open dispute{s}"))
    if score_drop is not None and score_drop >= 20:
        terms.append((10, f"Score fell {score_drop} points since last audit"))
    if no_counted_audit_30d:
        terms.append((15, "No verified audit in the last 30 days"))

    risk = round(sum(t for t, _ in terms))
    reasons = [r for t, r in sorted(terms, key=lambda x: -x[0]) if r and t > 0]
    return risk, reasons
