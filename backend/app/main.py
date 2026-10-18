"""KitchenProof API (FastAPI on Cloud Run). All routes live under /api (§11)."""

from __future__ import annotations

import logging
import math
import os
import random
import re
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import checks as C
from . import gemini, service
from .agents import orchestrator, planner
from .config import settings
from .demo import seed as demo_seed
from .firestore import Store, get_store
from .models import (
    AdvanceBody,
    CompleteBody,
    CreateAuditBody,
    DemoOrderBody,
    DemoSampleBody,
    DisputeBody,
    InspectorVisitBody,
    ReviewBody,
    StartBody,
    SurpriseBody,
)
from .prompts.version import PROMPT_VERSION
from .timeutil import IST, utcnow

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kitchenproof")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.demo_mode:
        try:
            store = get_store()
            if store.get("restaurants", demo_seed.HERO_ID) is None:
                log.info("Seeding demo data")
                demo_seed.seed(store)
        except Exception:  # noqa: BLE001 - never block startup on seeding
            log.exception("Demo seeding failed")
    yield


app = FastAPI(title="KitchenProof API", lifespan=lifespan)
api = APIRouter(prefix="/api")


def db() -> Store:
    return get_store()


# ---------- helpers ----------


def _get(path: str, doc_id: str, what: str) -> dict:
    doc = db().get(path, doc_id)
    if not doc:
        raise HTTPException(404, f"{what} not found")
    return doc


def distance_m(a: dict, b: dict) -> float:
    r = 6371000
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp = p2 - p1
    dl = math.radians(b["lng"] - a["lng"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def active_order(store: Store, restaurant_id: str) -> dict | None:
    orders = [
        o for o in store.query("orders", [("restaurantId", "==", restaurant_id)]) if o.get("status") == "preparing"
    ]
    return max(orders, key=lambda o: o["createdAt"]) if orders else None


def create_audit(store: Store, rest: dict, trigger: str, order_id: str | None, requested_by: str) -> dict:
    previous = sorted(
        store.query("audits", [("restaurantId", "==", rest["id"])]), key=lambda a: a["createdAt"]
    )
    prev_checks = None
    if previous:
        sec = store.get("auditSecrets", previous[-1]["id"])
        prev_checks = (sec or {}).get("plannedChecks")
    audit, secrets = planner.plan_audit(rest, trigger, order_id, requested_by, prev_checks)
    audit["ordersLastHourAtAudit"] = rest.get("ordersLastHour", 0)
    audit["demo"] = settings.demo_mode
    audit_id = store.add("audits", audit, prefix="a_")
    store.set("auditSecrets", audit_id, secrets)
    return {**audit, "id": audit_id}


def _reveal(store: Store, audit: dict, secrets: dict, index: int, offset: float) -> dict:
    seq = secrets["sequence"]
    item = seq[index]
    checks_so_far = sum(1 for s in seq[: index + 1] if s["kind"] == "check")
    total = sum(1 for s in seq if s["kind"] == "check")
    instr = planner.instruction_for(item, secrets, audit.get("orderId"), index, total, checks_so_far)
    now = utcnow()
    update: dict = {"cursor": index}
    if item["kind"] == "check":
        update["revealedChecks"] = (audit.get("revealedChecks") or []) + [
            {"checkId": item["checkId"], "prompt": instr["prompt"], "revealedAtServer": now, "offsetSec": round(offset, 1)}
        ]
    else:
        update["liveness"] = {"prompt": instr["prompt"], "revealedAtServer": now, "offsetSec": round(offset, 1)}
    store.update("audits", audit["id"], update)
    return instr


def _current_instruction(audit: dict, secrets: dict) -> dict | None:
    cursor = audit.get("cursor", -1)
    seq = secrets["sequence"]
    if cursor < 0 or cursor >= len(seq):
        return None
    total = sum(1 for s in seq if s["kind"] == "check")
    checks_so_far = sum(1 for s in seq[: cursor + 1] if s["kind"] == "check")
    return planner.instruction_for(seq[cursor], secrets, audit.get("orderId"), cursor, total, checks_so_far)


def _expire_if_overdue(audit: dict) -> dict:
    now = utcnow()
    if audit["status"] == "requested" and now > audit["startDeadlineAt"]:
        service.expire_overdue(db())
        raise HTTPException(410, "The 10-minute start window has passed. This was recorded as a missed check.")
    if (
        audit["status"] == "in_progress"
        and audit.get("finishDeadlineAt")
        and not audit.get("recordingEndedAt")
        and now > audit["finishDeadlineAt"] + timedelta(seconds=service.FINISH_GRACE_SEC)
    ):
        service.expire_overdue(db())
        raise HTTPException(410, "The 4-minute audit window has passed. This was recorded as a missed check.")
    return audit


def audit_view(audit: dict, with_findings: bool = True) -> dict:
    out = {k: v for k, v in audit.items() if k not in ("cursor",)}
    if with_findings:
        findings = db().query(f"audits/{audit['id']}/findings")
        findings.sort(key=lambda f: (C.SEVERITY_ORDER.get(f.get("severity", "low"), 9), f["checkId"]))
        out["findings"] = findings
    return out


def public_outcome(a: dict) -> dict:
    integrity = (a.get("integrity") or {}).get("verdict")
    if a.get("voided"):
        label, tone = "Voided after inspector visit", "bad"
    elif a["status"] == "expired":
        label, tone = "Missed check", "bad"
    elif integrity == "failed":
        label, tone = "Failed verification", "bad"
    elif a["status"] == "under_review" or integrity == "suspicious":
        label, tone = "Under review", "neutral"
    elif a.get("outcome") == "inconclusive" or a["status"] == "inconclusive":
        label, tone = "Inconclusive — re-audit requested", "neutral"
    elif a.get("counted"):
        n = a.get("issuesFound", 0)
        label = f"Kitchen Score {a['score']} · {n} issue{'s' if n != 1 else ''} found"
        tone = "good" if a["score"] >= 75 else "warn" if a["score"] >= 50 else "bad"
    elif a["status"] in ("requested", "in_progress", "uploaded", "analyzing"):
        label, tone = "In progress", "neutral"
    else:
        label, tone = a["status"].replace("_", " ").capitalize(), "neutral"
    return {
        "auditId": a["id"],
        "trigger": a["trigger"],
        "at": a.get("completedAt") or a.get("createdAt"),
        "label": label,
        "tone": tone,
    }


# ---------- audits ----------


@api.post("/audits")
def create_audit_route(body: CreateAuditBody):
    store = db()
    rest = _get("restaurants", body.restaurantId, "Restaurant")
    if body.trigger == "surprise":
        raise HTTPException(400, "Surprise audits are created by the platform, not by request.")

    order_id = body.orderId
    requested_by = "owner"
    if body.trigger == "customer":
        if not body.orderId or not body.customerId:
            raise HTTPException(400, "Customer checks need an active order.")
        order = _get("orders", body.orderId, "Order")
        if order["restaurantId"] != rest["id"] or order.get("customerId") != body.customerId:
            raise HTTPException(403, "You can only request a check on your own order.")
        if order.get("status") != "preparing":
            raise HTTPException(409, "Checks can only be requested while your order is being prepared.")
        if order.get("spotCheckAuditId"):
            raise HTTPException(409, "You already requested a check for this order.")
        now = utcnow()
        limit_id = f"{body.customerId}_{rest['id']}"
        limit = store.get("spotCheckLimits", limit_id)
        if limit and now - limit["lastRequestAt"] < timedelta(days=settings.customer_cooldown_days):
            raise HTTPException(429, f"You can request one check per restaurant every {settings.customer_cooldown_days} days.")
        today_ist = now.astimezone(IST).date()
        today_count = sum(
            1
            for a in store.query("audits", [("restaurantId", "==", rest["id"])])
            if a["trigger"] == "customer" and a["createdAt"].astimezone(IST).date() == today_ist
        )
        if today_count >= settings.customer_checks_per_day:
            raise HTTPException(429, f"This kitchen already had {today_count} customer checks today. Please try tomorrow.")
        requested_by = body.customerId
    else:
        order = active_order(store, rest["id"])
        order_id = order["id"] if order else None

    audit = create_audit(store, rest, body.trigger, order_id, requested_by)
    if body.trigger == "customer":
        store.set("spotCheckLimits", f"{body.customerId}_{rest['id']}", {"lastRequestAt": utcnow()})
        store.update("orders", body.orderId, {"spotCheckAuditId": audit["id"]})
    return {"auditId": audit["id"], "startDeadlineAt": audit["startDeadlineAt"], "trigger": audit["trigger"]}


@api.post("/audits/{audit_id}/reaudit")
def reaudit(audit_id: str):
    """Quick re-audit for an inconclusive audit (coverage < 70%), same trigger (§5.2 #4)."""
    store = db()
    audit = _get("audits", audit_id, "Audit")
    if audit.get("outcome") != "inconclusive" and audit["status"] != "inconclusive":
        raise HTTPException(409, "Only inconclusive audits can be re-audited.")
    if audit.get("reauditId"):
        return {"auditId": audit["reauditId"]}
    if audit.get("completedAt") and utcnow() - audit["completedAt"] > timedelta(hours=2):
        raise HTTPException(410, "The re-audit window (2 hours) has passed.")
    rest = _get("restaurants", audit["restaurantId"], "Restaurant")
    new = create_audit(store, rest, audit["trigger"], audit.get("orderId"), audit.get("requestedBy", "owner"))
    store.update("audits", new["id"], {"reauditOf": audit_id})
    store.update("audits", audit_id, {"reauditId": new["id"]})
    if audit["trigger"] == "customer" and audit.get("orderId"):
        store.update("orders", audit["orderId"], {"spotCheckAuditId": new["id"]})
    return {"auditId": new["id"], "startDeadlineAt": new["startDeadlineAt"]}


@api.get("/audits/{audit_id}")
def get_audit(audit_id: str):
    audit = _get("audits", audit_id, "Audit")
    if audit["status"] in service.OPEN_STATUSES:
        service.expire_overdue(db())
        audit = _get("audits", audit_id, "Audit")
    out = audit_view(audit)
    if audit["status"] == "in_progress":
        out["currentInstruction"] = _current_instruction(audit, db().get("auditSecrets", audit_id))
    return out


@api.post("/audits/{audit_id}/start")
def start_audit(audit_id: str, body: StartBody):
    store = db()
    audit = _get("audits", audit_id, "Audit")
    secrets = _get("auditSecrets", audit_id, "Audit plan")
    if audit["status"] == "in_progress":  # resume after a reload
        _expire_if_overdue(audit)
        return {"instruction": _current_instruction(audit, secrets), "finishDeadlineAt": audit["finishDeadlineAt"]}
    if audit["status"] != "requested":
        raise HTTPException(409, f"Audit is already {audit['status']}.")
    _expire_if_overdue(audit)

    now = utcnow()
    rest = _get("restaurants", audit["restaurantId"], "Restaurant")
    update: dict = {
        "status": "in_progress",
        "startedAt": now,
        "finishDeadlineAt": now + timedelta(minutes=settings.finish_window_min),
    }
    if body.gps:
        update["gps"] = body.gps.model_dump()
        update["distanceFromRegisteredM"] = round(distance_m(body.gps.model_dump(), rest["geo"]))
    store.update("audits", audit_id, update)
    audit = {**audit, **update}
    instruction = _reveal(store, audit, secrets, 0, 0.0)
    return {"instruction": instruction, "finishDeadlineAt": update["finishDeadlineAt"]}


@api.post("/audits/{audit_id}/advance")
def advance_audit(audit_id: str, body: AdvanceBody):
    store = db()
    audit = _get("audits", audit_id, "Audit")
    secrets = _get("auditSecrets", audit_id, "Audit plan")
    if audit["status"] != "in_progress":
        raise HTTPException(409, f"Audit is {audit['status']}.")
    if audit.get("recordingEndedAt"):
        return {"done": True}
    _expire_if_overdue(audit)
    cursor = audit.get("cursor", -1)
    if body.fromIndex is not None and body.fromIndex != cursor:
        # duplicate tap: return the item already being shown
        return {"done": False, "instruction": _current_instruction(audit, secrets)}
    nxt = cursor + 1
    if nxt >= len(secrets["sequence"]):
        store.update("audits", audit_id, {"recordingEndedAt": utcnow(), "cursor": nxt})
        return {"done": True}
    return {"done": False, "instruction": _reveal(store, audit, secrets, nxt, body.offsetSec)}


@api.post("/audits/{audit_id}/complete")
def complete_audit(audit_id: str, body: CompleteBody, background: BackgroundTasks):
    store = db()
    audit = _get("audits", audit_id, "Audit")
    if audit["status"] in ("uploaded", "analyzing"):
        return {"status": audit["status"]}
    if audit["status"] != "in_progress":
        raise HTTPException(409, f"Audit is {audit['status']}.")
    if not audit.get("recordingEndedAt"):
        _expire_if_overdue(audit)
        store.update("audits", audit_id, {"recordingEndedAt": utcnow()})
    if not (body.videoPath.startswith("audits/") or body.videoPath.startswith("local:")):
        raise HTTPException(400, "Video must be uploaded from the in-app camera.")
    store.update(
        "audits",
        audit_id,
        {"status": "uploaded", "videoPath": body.videoPath, "videoMime": body.videoMime, "durationSec": body.durationSec},
    )
    ref = orchestrator.resolve_video_ref(body.videoPath)
    background.add_task(_run_analysis, audit_id, ref, body.videoMime, None)
    return {"status": "analyzing"}


def _run_analysis(audit_id: str, ref: str, mime: str, sample: str | None) -> None:
    try:
        orchestrator.analyze(db(), audit_id, ref, mime, sample)
    except Exception:  # noqa: BLE001
        log.exception("Analysis crashed for %s", audit_id)
        db().update("audits", audit_id, {"status": "inconclusive", "outcome": "inconclusive", "analysisError": "Analysis crashed"})


@api.post("/audits/{audit_id}/demo-sample")
def demo_sample(audit_id: str, body: DemoSampleBody, background: BackgroundTasks):
    if not settings.demo_mode:
        raise HTTPException(403, "Sample videos are only available in Demo Mode.")
    store = db()
    audit = _get("audits", audit_id, "Audit")
    if audit["status"] not in service.OPEN_STATUSES:
        raise HTTPException(409, f"Audit is already {audit['status']}.")
    _expire_if_overdue(audit)
    rest = _get("restaurants", audit["restaurantId"], "Restaurant")
    sample = orchestrator.load_sample(body.sample)

    # The sample video was filmed against a fixed timeline: adopt it as this audit's plan.
    check_ids = [c["checkId"] for c in sample["checks"]]
    live = sample.get("liveness")  # a sample may have no usable gesture on camera
    live_prompt = (
        f"Hold up {live['n']} finger{'s' if live['n'] != 1 else ''} in front of the {live['object']}" if live else None
    )
    sequence = [{"kind": "check", "checkId": c["checkId"], "offsetSec": c["offsetSec"]} for c in sample["checks"]]
    if live:
        sequence.append({"kind": "liveness", "offsetSec": live["offsetSec"]})
    sequence.sort(key=lambda s: s["offsetSec"])
    store.update(
        "auditSecrets",
        audit_id,
        {
            "plannedChecks": check_ids,
            "sequence": [{k: v for k, v in s.items() if k != "offsetSec"} for s in sequence],
            "livenessExpected": {"n": live["n"], "object": live["object"]} if live else None,
            "livenessPrompt": live_prompt,
        },
    )
    now = utcnow()
    orders_last_hour = rest.get("ordersLastHour", 0)
    if body.sample == "too_perfect":
        orders_last_hour = max(orders_last_hour, 25)
    store.update(
        "audits",
        audit_id,
        {
            "status": "uploaded",
            "startedAt": audit.get("startedAt") or now,
            "finishDeadlineAt": audit.get("finishDeadlineAt") or now + timedelta(minutes=settings.finish_window_min),
            "recordingEndedAt": now,
            "requestedChecks": len(check_ids),
            "revealedChecks": [
                {"checkId": c["checkId"], "prompt": C.prompt_for(c["checkId"], audit.get("orderId")), "revealedAtServer": now, "offsetSec": c["offsetSec"]}
                for c in sample["checks"]
            ],
            "liveness": {"prompt": live_prompt, "revealedAtServer": now, "offsetSec": live["offsetSec"]} if live else None,
            "gps": {**rest["geo"], "accuracy": 10},
            "distanceFromRegisteredM": 0,
            "videoPath": f"demo:{body.sample}",
            "videoMime": sample["mime"],
            "durationSec": sample["durationSec"],
            "ordersLastHourAtAudit": orders_last_hour,
            "sample": body.sample,
        },
    )
    background.add_task(_run_analysis, audit_id, orchestrator.sample_video_ref(sample), sample["mime"], body.sample)
    return {"status": "analyzing", "sample": body.sample}


@api.post("/audits/{audit_id}/upload")
async def upload_local(audit_id: str, file: UploadFile = File(...)):
    """Local-dev upload when Cloud Storage for Firebase is not configured."""
    _get("audits", audit_id, "Audit")
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(400, "Only video uploads are accepted.")
    ext = "mp4" if "mp4" in (file.content_type or "") else "webm"
    os.makedirs(settings.local_media_dir, exist_ok=True)
    name = f"{audit_id}.{ext}"
    with open(os.path.join(settings.local_media_dir, name), "wb") as fh:
        while chunk := await file.read(1 << 20):
            fh.write(chunk)
    return {"videoPath": f"local:{name}"}


@api.get("/media/{name}")
def local_media(name: str):
    if not re.fullmatch(r"[A-Za-z0-9_]+\.(webm|mp4)", name):
        raise HTTPException(404)
    path = os.path.join(settings.local_media_dir, name)
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path)


# ---------- findings + review ----------


@api.post("/findings/{audit_id}/{finding_id}/dispute")
def dispute_finding(audit_id: str, finding_id: str, body: DisputeBody):
    store = db()
    audit = _get("audits", audit_id, "Audit")
    finding = _get(f"audits/{audit_id}/findings", finding_id, "Finding")
    if finding.get("disputed"):
        raise HTTPException(409, "This finding is already disputed.")
    if finding["status"] == "pass":
        raise HTTPException(400, "Only failed or unverified findings can be disputed.")
    store.update(
        f"audits/{audit_id}/findings",
        finding_id,
        {"disputed": True, "dispute": {"reason": body.reason, "at": utcnow()}},
    )
    service.queue_review(store, type_="dispute", audit=audit, finding_id=finding_id, detail=body.reason)
    return audit_view(service.rescore_audit(store, audit_id))


@api.get("/review")
def review_queue():
    store = db()
    items = store.query("reviewQueue")
    out = []
    for q in sorted(items, key=lambda q: (q["status"] != "open", -q["createdAt"].timestamp())):
        audit = store.get("audits", q["auditId"]) or {}
        entry = {**q, "audit": {k: audit.get(k) for k in ("id", "trigger", "score", "status", "videoPath", "integrity", "completedAt", "liveness", "ordersLastHourAtAudit")}}
        if q.get("findingId"):
            entry["finding"] = store.get(f"audits/{q['auditId']}/findings", q["findingId"])
        out.append(entry)
    return {"items": out[:60]}


@api.post("/review/{item_id}")
def resolve_review(item_id: str, body: ReviewBody):
    try:
        audit = service.resolve_review(db(), item_id, body.decision, body.by)
    except KeyError as err:
        raise HTTPException(404, str(err)) from err
    except ValueError as err:
        raise HTTPException(400, str(err)) from err
    return audit_view(audit)


# ---------- inspector + scheduler ----------


def _surprise(restaurant_id: str | None, requested_by: str) -> dict:
    store = db()
    if restaurant_id:
        rest = _get("restaurants", restaurant_id, "Restaurant")
    else:
        busy = {a["restaurantId"] for s in service.OPEN_STATUSES for a in store.query("audits", [("status", "==", s)])}
        candidates = [r for r in store.query("restaurants") if r["id"] not in busy] or store.query("restaurants")
        rest = random.choice(candidates)
    order = active_order(store, rest["id"])
    audit = create_audit(store, rest, "surprise", order["id"] if order else None, requested_by)
    return {"auditId": audit["id"], "restaurantId": rest["id"], "restaurantName": rest["name"], "startDeadlineAt": audit["startDeadlineAt"]}


@api.post("/inspector/surprise")
def inspector_surprise(body: SurpriseBody):
    return _surprise(body.restaurantId, "inspector")


@api.post("/inspector/visit")
def inspector_visit(body: InspectorVisitBody):
    _get("restaurants", body.restaurantId, "Restaurant")
    return service.record_inspector_visit(db(), body.restaurantId, body.outcome)


def _is_peak(hour: int) -> bool:
    return 12 <= hour < 15 or 19 <= hour < 23


@api.post("/scheduler/surprise")
def scheduler_surprise(x_scheduler_secret: str | None = Header(default=None)):
    if not settings.scheduler_secret or x_scheduler_secret != settings.scheduler_secret:
        raise HTTPException(401, "Bad scheduler secret")
    hour = utcnow().astimezone(IST).hour
    if not _is_peak(hour):
        return {"created": [], "note": "outside peak hours"}
    rng = random.SystemRandom()
    created = []
    for rest in db().query("restaurants"):
        # ~1 surprise per restaurant per day across 7 peak hours, run every 30 min
        if rng.random() < 1 / 14:
            created.append(_surprise(rest["id"], "system"))
    return {"created": created}


@api.post("/maintenance/expire")
def maintenance_expire():
    return {"expired": service.expire_overdue(db())}


@api.get("/risk/ranking")
def risk_ranking():
    store = db()
    service.expire_overdue(store)
    ranked = []
    for rest in store.query("restaurants"):
        r = service.recompute_restaurant(store, rest["id"])
        ranked.append(r)
    ranked.sort(key=lambda r: -(r.get("riskScore") or 0))
    return {"restaurants": [{**r, "rank": i + 1} for i, r in enumerate(ranked)]}


# ---------- restaurants + orders (read models for the web app) ----------


@api.get("/restaurants")
def list_restaurants():
    rests = db().query("restaurants")
    rests.sort(key=lambda r: r["id"])
    return {"restaurants": rests}


@api.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    store = db()
    rest = _get("restaurants", restaurant_id, "Restaurant")
    if rest.get("failedVerificationUntil") or rest.get("lastCountedAuditAt"):
        rest = service.recompute_restaurant(store, restaurant_id) or rest  # keeps decay fresh
    audits = sorted(
        store.query("audits", [("restaurantId", "==", restaurant_id)]), key=lambda a: a["createdAt"], reverse=True
    )
    public = [public_outcome(a) for a in audits if a["trigger"] != "practice"]
    rest["timeline"] = public[:10]
    rest["activeOrder"] = active_order(store, restaurant_id)
    return rest


@api.get("/restaurants/{restaurant_id}/audits")
def restaurant_audits(restaurant_id: str):
    """Owner/inspector view: every audit with outcome; open requests first."""
    _get("restaurants", restaurant_id, "Restaurant")
    audits = sorted(
        db().query("audits", [("restaurantId", "==", restaurant_id)]), key=lambda a: a["createdAt"], reverse=True
    )
    return {"audits": [{**audit_view(a, with_findings=False), "outcomeLabel": public_outcome(a)} for a in audits]}


@api.get("/orders/{order_id}")
def get_order(order_id: str):
    order = _get("orders", order_id, "Order")
    rest = db().get("restaurants", order["restaurantId"])
    order["restaurantName"] = (rest or {}).get("name")
    if order.get("spotCheckAuditId"):
        audit = db().get("audits", order["spotCheckAuditId"])
        if audit:
            if audit["status"] in service.OPEN_STATUSES:
                service.expire_overdue(db())
                audit = db().get("audits", order["spotCheckAuditId"])
            order["spotCheck"] = {**public_outcome(audit), "status": audit["status"], "score": audit.get("score"),
                                  "startDeadlineAt": audit.get("startDeadlineAt"), "counted": audit.get("counted")}
    return order


# ---------- demo + health ----------


@api.post("/demo/order")
def demo_order(body: DemoOrderBody):
    if not settings.demo_mode:
        raise HTTPException(403, "Demo only")
    rest = _get("restaurants", body.restaurantId, "Restaurant")
    order_id = str(random.randint(4600, 9999))
    db().set(
        "orders",
        order_id,
        {
            "restaurantId": rest["id"],
            "customerId": body.customerId,
            "items": ["Chicken biryani", "Raita"] if "Biryani" in rest["name"] else ["Chef's special", "Lime soda"],
            "status": "preparing",
            "createdAt": utcnow(),
        },
    )
    return {"orderId": order_id}


@api.post("/demo/reset")
def demo_reset(x_admin_secret: str | None = Header(default=None)):
    if settings.admin_secret:
        if x_admin_secret != settings.admin_secret:
            raise HTTPException(401, "Bad admin secret")
    elif not settings.demo_mode:
        raise HTTPException(403, "Demo only")
    return demo_seed.seed(db())


@api.get("/config")
def config():
    return {
        "demoMode": settings.demo_mode,
        "model": settings.gemini_model,
        "geminiAvailable": gemini.available(),
        "promptVersion": PROMPT_VERSION,
        "heroRestaurantId": demo_seed.HERO_ID,
        "startWindowMin": settings.start_window_min,
        "finishWindowMin": settings.finish_window_min,
        "customerChecksPerDay": settings.customer_checks_per_day,
        "customerCooldownDays": settings.customer_cooldown_days,
        "demoResetOpen": settings.demo_mode and not settings.admin_secret,
    }


@api.get("/health")
def health():
    return {"ok": True, "model": settings.gemini_model}


app.include_router(api)
