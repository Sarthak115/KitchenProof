"""Seed data for Demo Mode: 15 made-up Bhubaneswar restaurants with varied histories (§7.6).

All names and data are fictional.
"""

from __future__ import annotations

import os
import random
from datetime import timedelta

from .. import checks as C
from .. import service
from ..agents import scorer
from ..firestore import Store
from ..prompts.version import PROMPT_VERSION
from ..timeutil import utcnow

HERO_ID = "r01"  # the owner restaurant used by the guided tour

# The team's own kitchen stands in for the hero restaurant in live camera demos. Its check profile lists
# only what that kitchen can physically show (no floor drain, licence board, thermometer or pest
# certificate); the order of checks and the liveness gesture stay random.
HERO_CHECK_PROFILE = ["fridge_segregation", "handwash", "dustbins", "surfaces", "dry_storage", "labels_expiry"]
HERO_LIVENESS_OBJECTS = ["stove", "fridge", "sink"]


def _demo_kitchen_geo(default: dict) -> dict:
    """DEMO_KITCHEN_LATLNG="lat;lng" registers the real kitchen's location so the 200 m check passes."""
    raw = os.getenv("DEMO_KITCHEN_LATLNG", "")
    try:
        lat, lng = (float(v) for v in raw.replace(",", ";").split(";"))
        return {"lat": lat, "lng": lng}
    except ValueError:
        return default

COLLECTIONS = ["restaurants", "orders", "audits", "auditSecrets", "reviewQueue", "spotCheckLimits"]

# The clean sample video follows this check order; seeded clips point into it.
SAMPLE_CLIPS = {"fridge_segregation": 6, "handwash": 24, "dustbins": 42, "surfaces": 79, "labels_expiry": 116}
SAMPLE_CHECKS = list(SAMPLE_CLIPS) + ["handler_hygiene"]

REASONS_PASS = {
    "pests": "Floor under the stove and corners are clear of droppings or insects.",
    "fridge_segregation": "Raw meat is covered on the bottom shelf, below cooked food.",
    "fridge_temp": "Thermometer reads 4 °C.",
    "handwash": "Soap present, water running, basin clean.",
    "handler_hygiene": "Head covering, gloves and clean apron visible.",
    "order_prep": "Order is being plated with gloved hands.",
    "dustbins": "Lids closed, bins not overflowing.",
    "surfaces": "Counter and boards are clean.",
    "drains": "Grating in place, no standing waste.",
    "dry_storage": "Sacks are on racks off the floor and closed.",
    "labels_expiry": "Expiry dates are readable and in date.",
    "oil_condition": "Oil looks clear and golden.",
    "walls_ceiling": "Walls above the stove are clean.",
    "fssai_board": "FSSAI licence is displayed and readable.",
    "pest_control_record": "Pest control certificate dated last month is visible.",
    "water_source": "RO filter present and clean.",
}
REASONS_FAIL = {
    "pests": "Cockroach droppings visible along the wall behind the stove.",
    "fridge_segregation": "Uncovered raw fish on the top shelf above cooked dal.",
    "fridge_temp": "Thermometer reads 11 °C.",
    "handwash": "No soap at the handwash sink.",
    "handler_hygiene": "Cook has no head covering while handling food.",
    "order_prep": "Food plated with bare hands next to raw vegetables.",
    "dustbins": "Dustbin without a lid, overflowing.",
    "surfaces": "Grease and food residue build-up on the main counter.",
    "drains": "Floor drain has no grating and standing waste.",
    "dry_storage": "Open rice sack stored directly on the floor.",
    "labels_expiry": "Sauce bottle expired two weeks ago.",
    "oil_condition": "Frying oil is very dark and foaming.",
    "walls_ceiling": "Heavy grease and peeling paint above the stove.",
    "fssai_board": "No FSSAI licence visible.",
    "pest_control_record": "No pest control record could be shown.",
    "water_source": "Water filter housing is dirty.",
}

DISPUTE_REASONS = {
    "fridge_temp": "The fridge door had just been opened for a delivery; the thermometer reads 4 °C now.",
    "drains": "The grating was lifted only while the drain was being cleaned.",
}

# fmt: off
RESTAURANTS = [
    # id, name, cuisine, rating, area, lat, lng, ordersLastHour, inspectorVisitDaysAgo
    ("r01", "Kalinga Biryani House", "Biryani · Mughlai", 4.3, "Saheed Nagar", 20.2961, 85.8445, 6, None),
    ("r02", "Odisha Rasoi", "Odia thali", 4.5, "Old Town", 20.2376, 85.8338, 9, None),
    ("r03", "Chhena Poda Corner", "Sweets · Snacks", 4.6, "Kharavela Nagar", 20.2706, 85.8400, 6, 40),
    ("r04", "Mahanadi Fish Fry", "Seafood", 4.1, "Nayapalli", 20.2905, 85.8150, 11, None),
    ("r05", "Patia Pizza Co.", "Pizza · Fast food", 4.0, "Patia", 20.3540, 85.8190, 18, None),
    ("r06", "Jaydev Vihar Tiffins", "South Indian", 4.2, "Jaydev Vihar", 20.3000, 85.8250, 8, None),
    ("r07", "Dalma Junction", "Odia · Home style", 4.4, "Bapuji Nagar", 20.2600, 85.8370, 22, None),
    ("r08", "Khandagiri Momos", "Tibetan · Chinese", 4.0, "Khandagiri", 20.2560, 85.7800, 7, None),
    ("r09", "Cuttack Road Chinese", "Indo-Chinese", 3.9, "Rasulgarh", 20.2930, 85.8590, 12, None),
    ("r10", "Nayapalli Thali Ghar", "North Indian thali", 4.1, "Nayapalli", 20.2880, 85.8080, 10, None),
    ("r11", "Unit-9 Kebab Point", "Kebabs · Rolls", 3.8, "Unit 9", 20.2810, 85.8270, 15, None),
    ("r12", "Rasagola Express", "Sweets", 4.4, "Master Canteen", 20.2700, 85.8430, 5, None),
    ("r13", "Lingaraj Veg Bhojan", "Pure veg", 4.7, "Old Town", 20.2380, 85.8330, 9, 25),
    ("r14", "Infocity Cafe", "Cafe · Continental", 4.0, "Chandrasekharpur", 20.3330, 85.8100, 4, None),
    ("r15", "Rasulgarh Rolls & Shakes", "Rolls · Shakes", 4.2, "Rasulgarh", 20.2940, 85.8600, 6, None),
]

# Per restaurant: list of past audits. Keys: days ago, trigger, fails, nv (not verified),
# low (fail with low confidence → needs review), integrity, expired, dispute (checkId)
HISTORY = {
    "r01": [dict(days=12, trigger="surprise", fail=["walls_ceiling"])],
    "r02": [dict(days=20, trigger="surprise", fail=[]), dict(days=6, trigger="customer", fail=["drains"])],
    "r03": [dict(days=24, trigger="surprise", fail=[]), dict(days=9, trigger="customer", fail=[]),
            dict(days=3, trigger="surprise", fail=["fssai_board"])],
    "r04": [dict(days=18, trigger="surprise", fail=["oil_condition"]), dict(days=4, trigger="customer", fail=["dustbins", "surfaces"])],
    "r05": [dict(days=15, trigger="surprise", fail=["handwash"]),
            dict(days=2, trigger="customer", fail=["fridge_temp", "dustbins"], dispute="fridge_temp")],
    "r06": [dict(days=21, trigger="surprise", fail=["dry_storage"]), dict(days=8, trigger="surprise", expired=True),
            dict(days=3, trigger="customer", expired=True)],
    "r07": [dict(days=19, trigger="surprise", fail=["drains"]), dict(days=10, trigger="customer", fail=[]),
            dict(days=1, trigger="surprise", fail=[], integrity="suspicious")],
    "r08": [dict(days=11, trigger="practice", fail=["surfaces"]), dict(days=5, trigger="surprise", fail=["labels_expiry"], nv=["dry_storage"])],
    "r09": [dict(days=25, trigger="surprise", fail=["surfaces"]),
            dict(days=2, trigger="surprise", fail=["pests", "dustbins", "drains"], dispute="drains")],
    "r10": [dict(days=17, trigger="customer", fail=["walls_ceiling"]), dict(days=6, trigger="surprise", expired=True),
            dict(days=2, trigger="surprise", fail=["fridge_segregation", "handler_hygiene"])],
    "r11": [dict(days=14, trigger="surprise", fail=["oil_condition"]), dict(days=3, trigger="surprise", fail=[], integrity="failed")],
    "r12": [dict(days=52, trigger="surprise", fail=[]), dict(days=40, trigger="customer", fail=["dustbins"])],
    "r13": [dict(days=27, trigger="surprise", fail=[]), dict(days=12, trigger="customer", fail=[]),
            dict(days=4, trigger="surprise", fail=["water_source"])],
    "r14": [dict(days=65, trigger="surprise", fail=["surfaces"])],
    "r15": [dict(days=9, trigger="practice", fail=[]), dict(days=2, trigger="practice", fail=["drains"])],
}
# fmt: on


def _pick_checks(rng: random.Random, must: list[str]) -> list[str]:
    chosen = list(dict.fromkeys(must))
    for cid in SAMPLE_CHECKS + rng.sample(list(C.CHECKS), len(C.CHECKS)):
        if len(chosen) >= 6:
            break
        if cid not in chosen and cid != "order_prep":
            chosen.append(cid)
    return chosen


def _seed_audit(store: Store, rng: random.Random, rest: dict, spec: dict, n: int) -> None:
    now = utcnow()
    created = now - timedelta(days=spec["days"], hours=rng.randint(0, 6))
    audit_id = f"seed_{rest['id']}_{n}"
    base = {
        "restaurantId": rest["id"],
        "restaurantName": rest["name"],
        "trigger": spec["trigger"],
        "orderId": None,
        "requestedBy": "system" if spec["trigger"] == "surprise" else "seed",
        "createdAt": created,
        "startDeadlineAt": created + timedelta(minutes=10),
        "demo": True,
        "seeded": True,
    }
    if spec.get("expired"):
        store.set(
            "audits",
            audit_id,
            {**base, "status": "expired", "expiredReason": "not_started", "completedAt": created + timedelta(minutes=10), "counted": False},
        )
        return

    fails = spec.get("fail", [])
    nv = spec.get("nv", [])
    check_ids = _pick_checks(rng, fails + nv)
    findings = []
    for cid in check_ids:
        if cid in fails:
            findings.append(dict(checkId=cid, status="fail", reason=REASONS_FAIL[cid], confidence=round(rng.uniform(0.82, 0.95), 2)))
        elif cid in nv:
            findings.append(dict(checkId=cid, status="not_verified", reason="Not shown clearly in the video.", confidence=0.3))
        else:
            findings.append(dict(checkId=cid, status="pass", reason=REASONS_PASS[cid], confidence=round(rng.uniform(0.78, 0.95), 2)))
        findings[-1]["timestamp"] = f"0{len(findings) - 1}:{rng.randint(10, 50)}"
        findings[-1]["disputed"] = cid == spec.get("dispute")
        findings[-1]["dispute"] = (
            {"reason": DISPUTE_REASONS.get(cid, "This was cleaned before the check finished."), "at": created + timedelta(hours=2)}
            if cid == spec.get("dispute")
            else None
        )
        findings[-1]["review"] = None

    integrity_verdict = spec.get("integrity", "clean")
    flags = {
        "clean": [{"code": "liveness_ok", "detail": "Gesture matched the challenge.", "confidence": 0.88}],
        "suspicious": [
            {"code": "too_perfect", "detail": "Spotless, inactive kitchen with no cooking visible (22 orders in the last hour)", "confidence": 0.84},
            {"code": "props_suspected", "detail": "All ingredient packs brand-new and unopened.", "confidence": 0.7},
        ],
        "failed": [
            {"code": "liveness_failed", "detail": "Asked for 4 fingers at the sink; no gesture was shown.", "confidence": 0.86}
        ],
    }[integrity_verdict]

    scored = scorer.score_audit(findings, len(check_ids), integrity_verdict, spec["trigger"])
    for f in scored["findings"]:
        store.set(f"audits/{audit_id}/findings", f["checkId"], f)
    clips = [
        {"checkId": f["checkId"], "startSec": SAMPLE_CLIPS[f["checkId"]], "endSec": SAMPLE_CLIPS[f["checkId"]] + 4}
        for f in scored["findings"]
        if f["checkId"] in SAMPLE_CLIPS and f["effectiveStatus"] == "pass"
    ]
    started = created + timedelta(minutes=rng.randint(1, 8))
    store.set(
        "audits",
        audit_id,
        {
            **base,
            "status": scored["status"],
            "outcome": scored["status"],
            "startedAt": started,
            "completedAt": started + timedelta(minutes=3),
            "requestedChecks": len(check_ids),
            "checkOrder": check_ids,
            "revealedChecks": [
                {"checkId": cid, "prompt": C.prompt_for(cid), "offsetSec": i * 20} for i, cid in enumerate(check_ids)
            ],
            "score": scored["score"],
            "coverage": scored["coverage"],
            "counted": scored["counted"],
            "issuesFound": scored["issuesFound"],
            "integrity": {"verdict": integrity_verdict, "flags": flags},
            "evidenceClips": clips,
            "observedItems": [],
            "videoPath": "demo:clean",
            "videoMime": "video/mp4",
            "durationSec": 140,
            "gps": {"lat": rest["geo"]["lat"], "lng": rest["geo"]["lng"], "accuracy": 15},
            "distanceFromRegisteredM": round(rng.uniform(5, 40)),
            "coach": None,
            "modelId": "seeded-demo-data",
            "promptVersion": PROMPT_VERSION,
            "usedCachedResult": False,
        },
    )
    audit = store.get("audits", audit_id)
    queued_at = audit["completedAt"] + timedelta(hours=2)
    if spec.get("dispute"):
        service.queue_review(store, type_="dispute", audit=audit, finding_id=spec["dispute"], detail=REASONS_FAIL[spec["dispute"]], at=queued_at)
    if integrity_verdict in ("suspicious", "failed"):
        service.queue_review(store, type_="integrity", audit=audit, detail=", ".join(f["code"] for f in flags), at=queued_at)
    if integrity_verdict == "failed":
        service.mark_failed_verification(store, rest["id"])
    if spec.get("dispute") or integrity_verdict != "clean":
        store.update("audits", audit_id, {"status": "under_review"})


def seed(store: Store) -> dict:
    store.wipe(COLLECTIONS)
    now = utcnow()
    rng = random.Random(4521)
    for i, (rid, name, cuisine, rating, area, lat, lng, olh, visit) in enumerate(RESTAURANTS):
        rest = {
            "id": rid,
            "name": name,
            "cuisine": cuisine,
            "rating": rating,
            "address": f"{area}, Bhubaneswar, Odisha",
            "area": area,
            "geo": {"lat": lat, "lng": lng},
            "fssaiLicense": f"1202{rng.randint(10**9, 10**10 - 1)}",
            "demo": True,
            "ordersLastHour": olh,
            "publicScore": None,
            "tier": "bronze",
            "failedVerificationUntil": None,
            "referenceSummary": None,
            "referenceAuditId": None,
            "inspectorVisitAt": now - timedelta(days=visit) if visit else None,
            "riskScore": 0,
            "riskReasons": [],
        }
        if rid == HERO_ID:
            rest["checkProfile"] = HERO_CHECK_PROFILE
            rest["livenessObjects"] = HERO_LIVENESS_OBJECTS
            rest["geo"] = _demo_kitchen_geo(rest["geo"])
        store.set("restaurants", rid, rest)
        store.set(
            "orders",
            f"{4521 + i}",
            {
                "restaurantId": rid,
                "customerId": "demo-customer",
                "items": ["Chicken biryani", "Raita"] if rid == HERO_ID else ["Today's special"],
                "status": "preparing",
                "createdAt": now - timedelta(minutes=8),
            },
        )
        for n, spec in enumerate(HISTORY.get(rid, [])):
            _seed_audit(store, rng, rest, spec, n)
        # inspector-confirmed audits carry extra weight
        if visit:
            latest = max(
                (a for a in store.query("audits", [("restaurantId", "==", rid)]) if a.get("counted")),
                key=lambda a: a["completedAt"],
            )
            store.update("audits", latest["id"], {"inspectorConfirmed": True})
        service.recompute_restaurant(store, rid)
    return {"restaurants": len(RESTAURANTS), "seededAt": now}
