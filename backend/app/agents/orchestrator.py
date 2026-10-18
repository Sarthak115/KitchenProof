"""Orchestrator: auditor + integrity in parallel → scorer → coach → write → risk (§9)."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .. import gemini, service
from ..config import settings
from ..firestore import Store
from ..prompts.version import PROMPT_VERSION
from ..timeutil import utcnow
from . import auditor, coach, integrity, scorer

log = logging.getLogger(__name__)

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"


def load_sample(sample: str) -> dict:
    return json.loads((DEMO_DIR / "timelines" / f"{sample}.json").read_text())


def load_cached(sample: str) -> dict:
    return json.loads((DEMO_DIR / "cached_results" / f"{sample}.json").read_text())


def sample_video_ref(sample: dict) -> str:
    if settings.storage_bucket and settings.use_vertex:
        return f"gs://{settings.storage_bucket}/demo-assets/{sample['video']}"
    import os

    return os.path.join(os.getenv("DEMO_ASSETS_DIR", "../frontend/public/demo"), sample["video"])


def clamp_clips(clips: list[dict], duration: float | None) -> list[dict]:
    """Gemini sometimes places a clip past the end of the video; keep clips inside it."""
    if not duration:
        return clips
    out = []
    for c in clips:
        end = min(c["endSec"], duration)
        start = max(0.0, min(c["startSec"], end - 3))
        if end > start:
            out.append({**c, "startSec": start, "endSec": end})
    return out


def resolve_video_ref(video_path: str) -> str:
    """Map a stored videoPath to something Gemini can read."""
    if video_path.startswith("gs://"):
        return video_path
    if video_path.startswith("local:"):
        import os

        return os.path.join(settings.local_media_dir, video_path.removeprefix("local:"))
    if settings.storage_bucket:
        return f"gs://{settings.storage_bucket}/{video_path}"
    raise ValueError(f"cannot resolve video path {video_path}")


def _call_gemini(video_ref: str, mime: str, check_ids, timeline, liveness, audit, rest) -> tuple[dict, dict, str]:
    video = gemini.video_part(video_ref, mime)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(auditor.run, video, check_ids, timeline, liveness, audit.get("orderId"))
        fut_i = pool.submit(
            integrity.run,
            video,
            audit.get("ordersLastHourAtAudit", rest.get("ordersLastHour", 0)),
            audit["trigger"],
            rest.get("referenceSummary"),
        )
        aud, model_id = fut_a.result()
        integ, _ = fut_i.result()
    return aud, integ, model_id


def analyze(store: Store, audit_id: str, video_ref: str, mime: str, sample: str | None = None) -> dict:
    audit = store.get("audits", audit_id)
    secrets = store.get("auditSecrets", audit_id) or {}
    rest = store.get("restaurants", audit["restaurantId"])
    store.update("audits", audit_id, {"status": "analyzing"})

    check_ids: list[str] = secrets["plannedChecks"]
    timeline = audit.get("revealedChecks") or []
    liveness = audit.get("liveness")

    aud = integ = None
    coach_result = None
    model_id = settings.gemini_model
    used_cache = False
    error = None

    if gemini.available():
        try:
            aud, integ, model_id = _call_gemini(video_ref, mime, check_ids, timeline, liveness, audit, rest)
        except Exception as err:  # noqa: BLE001 - the demo must never dead-end
            log.exception("Gemini analysis failed for %s", audit_id)
            error = str(err)
    else:
        error = "Gemini is not configured"

    if aud is None and sample:
        cached = load_cached(sample)
        aud = auditor.normalize(cached["auditor"], check_ids)
        integ = cached["integrity"]
        coach_result = cached.get("coach")
        model_id = cached.get("modelId", model_id)
        used_cache = True

    if aud is None:
        store.update(
            "audits",
            audit_id,
            {
                "status": "inconclusive",
                "outcome": "inconclusive",
                "analysisError": error,
                "completedAt": utcnow(),
                "counted": False,
                "modelId": model_id,
                "promptVersion": PROMPT_VERSION,
            },
        )
        service.recompute_restaurant(store, audit["restaurantId"])
        return store.get("audits", audit_id)

    # --- integrity verdict (Gemini signals + rules)
    history = [
        a.get("observedItems") or []
        for a in store.query("audits", [("restaurantId", "==", audit["restaurantId"])])
        if a["id"] != audit_id
    ]
    integrity_result = integrity.verdict(
        gem=integ,
        liveness_obs=aud.get("liveness"),
        liveness_expected=secrets.get("livenessExpected"),
        distance_m=audit.get("distanceFromRegisteredM"),
        orders_last_hour=audit.get("ordersLastHourAtAudit", rest.get("ordersLastHour", 0)),
        has_reference=bool(rest.get("referenceSummary")),
        observed_items=aud.get("observedItems") or [],
        item_history=history,
        duration_sec=audit.get("durationSec"),
        planned_items=len(secrets.get("sequence") or check_ids),
    )
    integrity_result["kitchenSummary"] = (integ or {}).get("kitchenSummary")
    integrity_result["signals"] = integ

    # --- score
    scored = scorer.score_audit(aud["findings"], len(check_ids), integrity_result["verdict"], audit["trigger"])
    for f in scored["findings"]:
        store.set(
            f"audits/{audit_id}/findings",
            f["checkId"],
            {**f, "disputed": False, "dispute": None, "review": None},
        )

    # --- coach (text only)
    if coach_result is None:
        coach_result = coach.run(scored["findings"])

    now = utcnow()
    update = {
        "score": scored["score"],
        "coverage": scored["coverage"],
        "counted": scored["counted"],
        "outcome": scored["status"],
        "status": scored["status"],
        "issuesFound": scored["issuesFound"],
        "integrity": integrity_result,
        "liveness": {**liveness, "observed": aud.get("liveness")} if liveness else None,
        "observedItems": aud.get("observedItems") or [],
        "evidenceClips": clamp_clips(aud.get("evidenceClips") or [], audit.get("durationSec")),
        "checkOrder": check_ids,
        "coach": coach_result,
        "modelId": model_id,
        "promptVersion": PROMPT_VERSION,
        "usedCachedResult": used_cache,
        "analysisError": error if used_cache else None,
        "completedAt": now,
    }
    store.update("audits", audit_id, update)
    audit = {**audit, **update}

    if integrity_result["verdict"] == "failed":
        service.mark_failed_verification(store, audit["restaurantId"])
    if integrity_result["verdict"] in ("failed", "suspicious"):
        codes = ", ".join(f["code"] for f in integrity_result["flags"] if f["code"] not in ("liveness_ok",))
        service.queue_review(store, type_="integrity", audit=audit, detail=codes)
        store.update("audits", audit_id, {"status": "under_review"})
    elif (
        scored["status"] == "scored"
        and audit["trigger"] != "practice"
        and not rest.get("referenceSummary")
        and integrity_result.get("kitchenSummary")
    ):
        store.update(
            "restaurants",
            audit["restaurantId"],
            {"referenceSummary": integrity_result["kitchenSummary"], "referenceAuditId": audit_id},
        )

    service.recompute_restaurant(store, audit["restaurantId"])
    return store.get("audits", audit_id)
