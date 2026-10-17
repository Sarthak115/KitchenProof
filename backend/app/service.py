"""Shared domain operations: restaurant aggregates, expiry, rescoring and reviews."""

from __future__ import annotations

from datetime import datetime, timedelta

from .agents import risk as risk_agent
from .agents import scorer
from .firestore import Store
from .timeutil import days_between, utcnow

FAILED_VERIFICATION_DAYS = 30
FINISH_GRACE_SEC = 60  # extra time to press the last "Done" before an in-progress audit expires
OPEN_STATUSES = ("requested", "in_progress")


# ---------- restaurant aggregates ----------


def recompute_restaurant(store: Store, restaurant_id: str) -> dict | None:
    rest = store.get("restaurants", restaurant_id)
    if not rest:
        return None
    now = utcnow()
    audits = store.query("audits", [("restaurantId", "==", restaurant_id)])
    real = [a for a in audits if a["trigger"] != "practice" and not a.get("voided")]
    counted = sorted(
        [a for a in real if a.get("counted") and a.get("completedAt")], key=lambda a: a["completedAt"]
    )
    ps = scorer.public_score(counted, now)

    in_30d = lambda ts: ts is not None and days_between(now, ts) <= 30  # noqa: E731
    missed = sum(1 for a in real if a["status"] == "expired" and in_30d(a.get("createdAt")))
    integrity_issue = any(
        (a.get("integrity") or {}).get("verdict") in ("failed", "suspicious") and in_30d(a.get("completedAt"))
        for a in real
    )
    open_disputes = sum(
        1
        for q in store.query("reviewQueue", [("restaurantId", "==", restaurant_id)])
        if q["type"] == "dispute" and q["status"] == "open"
    )
    under_review = any(
        q["status"] == "open" for q in store.query("reviewQueue", [("restaurantId", "==", restaurant_id)])
    )
    score_drop = None
    if len(counted) >= 2:
        score_drop = counted[-2]["score"] - counted[-1]["score"]
    no_recent = ps["lastCountedAuditAt"] is None or not in_30d(ps["lastCountedAuditAt"])

    failed_until = rest.get("failedVerificationUntil")
    failed_active = bool(failed_until and failed_until > now)
    tier = scorer.tier(real, rest.get("inspectorVisitAt"), now)

    if failed_active:
        badge_state = "failed_verification"
    elif ps["notRecentlyVerified"]:
        badge_state = "not_recently_verified"
    elif ps["publicScore"] is None:
        badge_state = "unverified"
    else:
        badge_state = "scored"

    risk, reasons = risk_agent.compute(
        public_score=0 if failed_active else ps["publicScore"],
        missed_checks_30d=missed,
        integrity_issue_30d=integrity_issue,
        open_disputes=open_disputes,
        score_drop=score_drop,
        no_counted_audit_30d=no_recent,
    )
    if failed_active:
        reasons = ["Failed verification in the last 30 days"] + [r for r in reasons if not r.startswith("Kitchen Score")]

    last = counted[-1] if counted else None
    update = {
        "publicScore": ps["publicScore"],
        "scoreDecayed": ps["decayed"],
        "badgeState": badge_state,
        "tier": "bronze" if failed_active else tier,
        "lastCountedAuditAt": ps["lastCountedAuditAt"],
        "lastIssuesFound": last.get("issuesFound", 0) if last else None,
        "missedChecks30d": missed,
        "openDisputes": open_disputes,
        "underReview": under_review,
        "riskScore": risk,
        "riskReasons": reasons,
        "evidenceClips": public_clips(store, counted),
        "updatedAt": now,
    }
    store.update("restaurants", restaurant_id, update)
    return {**rest, **update}


def public_clips(store: Store, counted: list[dict]) -> list[dict]:
    """Up to 3 short surface/equipment clips from passing checks of the latest clean audit."""
    for audit in reversed(counted):
        if (audit.get("integrity") or {}).get("verdict") != "clean" or not audit.get("evidenceClips"):
            continue
        findings = {f["checkId"]: f for f in store.query(f"audits/{audit['id']}/findings")}
        clips = []
        for clip in audit["evidenceClips"]:
            f = findings.get(clip["checkId"])
            # handler checks may show people; keep public clips to surfaces/equipment
            if not f or f.get("effectiveStatus") != "pass" or clip["checkId"] in ("handler_hygiene", "order_prep"):
                continue
            end = min(clip["endSec"], clip["startSec"] + 5)
            clips.append(
                {
                    "auditId": audit["id"],
                    "checkId": clip["checkId"],
                    "startSec": clip["startSec"],
                    "endSec": end,
                    "videoPath": audit.get("videoPath"),
                    "verifiedAt": audit.get("completedAt"),
                }
            )
            if len(clips) == 3:
                break
        if clips:
            return clips
    return []


# ---------- expiry ----------


def expire_overdue(store: Store) -> list[str]:
    now = utcnow()
    expired = []
    touched = set()
    for status in OPEN_STATUSES:
        for a in store.query("audits", [("status", "==", status)]):
            reason = None
            if status == "requested" and a.get("startDeadlineAt") and now > a["startDeadlineAt"]:
                reason = "not_started"
            elif (
                status == "in_progress"
                and not a.get("recordingEndedAt")
                and a.get("finishDeadlineAt")
                and now > a["finishDeadlineAt"] + timedelta(seconds=FINISH_GRACE_SEC)
            ):
                reason = "not_finished"
            if reason:
                store.update("audits", a["id"], {"status": "expired", "expiredReason": reason, "completedAt": now})
                expired.append(a["id"])
                touched.add(a["restaurantId"])
    for rid in touched:
        recompute_restaurant(store, rid)
    return expired


# ---------- rescoring + reviews ----------


def rescore_audit(store: Store, audit_id: str) -> dict:
    audit = store.get("audits", audit_id)
    findings = store.query(f"audits/{audit_id}/findings")
    order = {cid: i for i, cid in enumerate(audit.get("checkOrder") or [])}
    findings.sort(key=lambda f: order.get(f["checkId"], 99))
    verdict = (audit.get("integrity") or {}).get("verdict", "clean")
    result = scorer.score_audit(findings, audit.get("requestedChecks") or len(findings), verdict, audit["trigger"])
    for f in result["findings"]:
        store.update(
            f"audits/{audit_id}/findings",
            f["id"],
            {k: f[k] for k in ("severity", "needsReview", "publicEligible", "effectiveStatus")},
        )
    open_items = [
        q for q in store.query("reviewQueue", [("auditId", "==", audit_id)]) if q["status"] == "open"
    ]
    had_items = bool(store.query("reviewQueue", [("auditId", "==", audit_id)]))
    status = "under_review" if open_items else "resolved" if had_items else result["status"]
    update = {
        "score": result["score"],
        "coverage": result["coverage"],
        "counted": result["counted"] and not audit.get("voided"),
        "outcome": result["status"],
        "status": status,
        "issuesFound": result["issuesFound"],
    }
    store.update("audits", audit_id, update)
    recompute_restaurant(store, audit["restaurantId"])
    return {**audit, **update}


def queue_review(
    store: Store, *, type_: str, audit: dict, finding_id: str | None = None, detail: str = "", at: datetime | None = None
) -> str:
    return store.add(
        "reviewQueue",
        {
            "type": type_,
            "auditId": audit["id"],
            "findingId": finding_id,
            "restaurantId": audit["restaurantId"],
            "restaurantName": audit.get("restaurantName"),
            "detail": detail,
            "createdAt": at or utcnow(),
            "status": "open",
        },
        prefix="rq_",
    )


def mark_failed_verification(store: Store, restaurant_id: str) -> None:
    store.update(
        "restaurants",
        restaurant_id,
        {"failedVerificationUntil": utcnow() + timedelta(days=FAILED_VERIFICATION_DAYS)},
    )


def resolve_review(store: Store, item_id: str, decision: str, by: str) -> dict:
    item = store.get("reviewQueue", item_id)
    if not item:
        raise KeyError("review item not found")
    if item["status"] != "open":
        raise ValueError("review item already resolved")
    now = utcnow()
    audit = store.get("audits", item["auditId"])

    if item["type"] == "dispute":
        if decision not in ("upheld", "overturned"):
            raise ValueError("dispute decisions are 'upheld' or 'overturned'")
        store.update(
            f"audits/{audit['id']}/findings",
            item["findingId"],
            {"review": {"decision": decision, "by": by, "at": now}},
        )
    else:
        if decision not in ("clear", "confirm_failed"):
            raise ValueError("integrity decisions are 'clear' or 'confirm_failed'")
        integrity = dict(audit.get("integrity") or {})
        integrity.setdefault("originalVerdict", integrity.get("verdict"))
        integrity["verdict"] = "clean" if decision == "clear" else "failed"
        integrity["review"] = {"decision": decision, "by": by, "at": now}
        store.update("audits", audit["id"], {"integrity": integrity})
        if decision == "confirm_failed":
            mark_failed_verification(store, audit["restaurantId"])
        elif integrity.get("originalVerdict") == "failed":
            store.update("restaurants", audit["restaurantId"], {"failedVerificationUntil": None})

    store.update("reviewQueue", item_id, {"status": "resolved", "decision": decision, "resolvedAt": now, "by": by})
    return rescore_audit(store, audit["id"])


def record_inspector_visit(store: Store, restaurant_id: str, outcome: str) -> dict:
    """§5.1 #11–12: a visit enables Gold; a contradicting visit voids the latest audit."""
    now = utcnow()
    audits = [
        a
        for a in store.query("audits", [("restaurantId", "==", restaurant_id)])
        if a.get("counted") and a.get("completedAt") and not a.get("voided")
    ]
    latest = max(audits, key=lambda a: a["completedAt"]) if audits else None
    if outcome == "confirmed":
        store.update("restaurants", restaurant_id, {"inspectorVisitAt": now})
        if latest:
            store.update("audits", latest["id"], {"inspectorConfirmed": True})
    else:
        if latest:
            store.update("audits", latest["id"], {"voided": True, "counted": False})
        mark_failed_verification(store, restaurant_id)
    return recompute_restaurant(store, restaurant_id)

