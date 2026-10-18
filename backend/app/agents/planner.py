"""Planner agent (deterministic): picks random checks + a liveness challenge (§6.2, §6.3).

The full sequence is stored in auditSecrets/{auditId} so the owner can never see the list in
advance; items are revealed one at a time through /start and /advance.
"""

from __future__ import annotations

import random
from datetime import timedelta

from .. import checks as C
from ..config import settings
from ..liveness import make_challenge
from ..timeutil import utcnow

CHECKS_PER_AUDIT = 6


def pick_checks(
    rng: random.Random,
    has_active_order: bool,
    previous: list[str] | None = None,
    allowed: list[str] | None = None,
) -> list[str]:
    """1–2 critical + 2–3 high + rest medium/low; order_prep always included with an active order.

    `allowed` is the restaurant's check profile: the checks its kitchen can physically show (a home-style
    kitchen may have no floor drain or licence board). With six or fewer allowed checks, all of them are
    used in a random order; otherwise the severity mix is drawn from the allowed ones only.
    """
    if allowed:
        pool = [c for c in dict.fromkeys(allowed) if c in C.CHECKS and (c != "order_prep" or has_active_order)]
        if len(pool) <= CHECKS_PER_AUDIT:
            rng.shuffle(pool)
            return pool
    else:
        pool = list(C.CHECKS)

    def bucket(*severities: str, exclude: set[str] = frozenset()) -> list[str]:
        return [c for sev in severities for c in C.by_severity(sev, exclude=set(exclude)) if c in pool]

    previous_set = set(previous or [])
    for _ in range(20):
        crit, high = bucket("critical"), bucket("high", exclude={"order_prep"})
        n_crit = min(rng.choice([1, 2]), len(crit))
        n_high = min(rng.choice([2, 3]), len(high) + (1 if has_active_order and "order_prep" in pool else 0))

        chosen = rng.sample(crit, n_crit)
        if has_active_order and "order_prep" in pool:
            chosen += ["order_prep"] + rng.sample(high, min(n_high - 1, len(high)))
        else:
            chosen += rng.sample(high, min(n_high, len(high)))
        rest = [c for c in bucket("medium", "low") if c not in chosen]
        chosen += rng.sample(rest, min(CHECKS_PER_AUDIT - len(chosen), len(rest)))

        rng.shuffle(chosen)
        if set(chosen) != previous_set:
            return chosen
    return chosen


def build_sequence(rng: random.Random, check_ids: list[str]) -> list[dict]:
    """Insert the liveness challenge after check 2, 3 or 4 (i.e. between checks 2 and 5)."""
    seq: list[dict] = [{"kind": "check", "checkId": c} for c in check_ids]
    pos = rng.choice([2, 3, 4])
    seq.insert(pos, {"kind": "liveness"})
    return seq


def plan_audit(
    restaurant: dict,
    trigger: str,
    order_id: str | None,
    requested_by: str,
    previous_checks: list[str] | None = None,
    rng: random.Random | None = None,
) -> tuple[dict, dict]:
    """Return (audit document, secrets document)."""
    rng = rng or random.SystemRandom()
    now = utcnow()
    check_ids = pick_checks(
        rng, has_active_order=bool(order_id), previous=previous_checks, allowed=restaurant.get("checkProfile")
    )
    challenge = make_challenge(rng, restaurant.get("livenessObjects"))
    sequence = build_sequence(rng, check_ids)

    audit = {
        "restaurantId": restaurant["id"],
        "restaurantName": restaurant.get("name"),
        "trigger": trigger,
        "orderId": order_id,
        "requestedBy": requested_by,
        "status": "requested",
        "createdAt": now,
        "startDeadlineAt": now + timedelta(minutes=settings.start_window_min),
        "startedAt": None,
        "finishDeadlineAt": None,
        "recordingEndedAt": None,
        "completedAt": None,
        "requestedChecks": len(check_ids),
        "revealedChecks": [],
        "liveness": None,
        "cursor": -1,
        "counted": False,
    }
    secrets = {
        "plannedChecks": check_ids,
        "sequence": sequence,
        "livenessExpected": {"n": challenge["n"], "object": challenge["object"]},
        "livenessPrompt": challenge["prompt"],
    }
    return audit, secrets


def instruction_for(item: dict, secrets: dict, order_id: str | None, index: int, total_checks: int, check_no: int) -> dict:
    if item["kind"] == "liveness":
        return {
            "kind": "liveness",
            "prompt": secrets["livenessPrompt"],
            "index": index,
            "checkNumber": check_no,
            "totalChecks": total_checks,
        }
    return {
        "kind": "check",
        "checkId": item["checkId"],
        "prompt": C.prompt_for(item["checkId"], order_id),
        "severity": C.CHECKS[item["checkId"]].severity,
        "index": index,
        "checkNumber": check_no,
        "totalChecks": total_checks,
    }
