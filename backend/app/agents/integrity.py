"""Integrity agent (Gemini + rules): is this a genuine, live, continuous take? (§5.1, §12.2)"""

from __future__ import annotations

from .. import gemini
from ..liveness import matches as liveness_matches
from ..models import IntegrityResult
from ._prompts import fill, load

SECONDS_PER_ITEM = 20  # expected time per check / liveness item
MAX_DISTANCE_M = 200


def build_prompt(orders_last_hour: int, trigger: str, reference_summary: str | None) -> str:
    return fill(
        load("integrity"),
        orders_last_hour=orders_last_hour,
        trigger=trigger,
        reference_summary=reference_summary or "none yet (this is the first verified audit)",
    )


def run(video, orders_last_hour: int, trigger: str, reference_summary: str | None) -> tuple[dict, str]:
    result, model_id = gemini.generate_json(
        build_prompt(orders_last_hour, trigger, reference_summary), IntegrityResult, video=video
    )
    return IntegrityResult.model_validate(result).model_dump(), model_id


def repeated_props(current_items: list[dict], history: list[list[dict]]) -> list[str]:
    """Same unopened item (same label + batch/expiry) seen in >= 3 audits incl. this one."""
    flagged = []
    for item in current_items:
        if item.get("state") != "unopened" or not item.get("batchOrExpiry"):
            continue
        key = (item["label"].strip().lower(), item["batchOrExpiry"].strip().lower())
        seen = 1 + sum(
            any(
                (h.get("label", "").strip().lower(), h.get("batchOrExpiry", "").strip().lower()) == key
                and h.get("state") == "unopened"
                for h in past
            )
            for past in history
        )
        if seen >= 3:
            flagged.append(f"{item['label']} ({item['batchOrExpiry']})")
    return flagged


def verdict(
    *,
    gem: dict | None,
    liveness_obs: dict | None,
    liveness_expected: dict | None,
    distance_m: float | None,
    orders_last_hour: int,
    has_reference: bool,
    observed_items: list[dict],
    item_history: list[list[dict]],
    duration_sec: float | None,
    planned_items: int,
) -> dict:
    """Combine Gemini signals with deterministic rules into clean | suspicious | failed."""
    failed: list[dict] = []
    suspicious: list[dict] = []
    info: list[dict] = []

    # --- liveness
    if liveness_expected and liveness_obs is not None:
        conf = float(liveness_obs.get("confidence") or 0)
        ok = liveness_matches(liveness_expected, liveness_obs.get("fingersCounted"), liveness_obs.get("nearObject"))
        detail = (
            f"Asked for {liveness_expected['n']} finger(s) at the {liveness_expected['object']}; "
            f"saw: {liveness_obs.get('observed') or 'nothing'}"
        )
        if not ok and conf >= 0.7:
            failed.append({"code": "liveness_failed", "detail": detail, "confidence": conf})
        elif not ok:
            info.append({"code": "liveness_unclear", "detail": detail, "confidence": conf})
        else:
            info.append({"code": "liveness_ok", "detail": detail, "confidence": conf})

    # --- location
    if distance_m is not None and distance_m > MAX_DISTANCE_M:
        failed.append(
            {
                "code": "wrong_location",
                "detail": f"Recorded {round(distance_m)} m from the registered address (limit {MAX_DISTANCE_M} m)",
                "confidence": 1.0,
            }
        )

    if gem:
        ct = gem["continuousTake"]
        if not ct["ok"] and ct["confidence"] >= 0.8:
            failed.append({"code": "edited_video", "detail": ct["detail"], "confidence": ct["confidence"]})
        elif not ct["ok"]:
            info.append({"code": "possible_cut", "detail": ct["detail"], "confidence": ct["confidence"]})

        sk = gem["sameKitchenAsReference"]
        if has_reference and not sk["ok"] and sk["confidence"] >= 0.6:
            suspicious.append({"code": "different_kitchen", "detail": sk["detail"], "confidence": sk["confidence"]})

        act = gem["activityMatchesOrders"]
        if not act["ok"] and act["confidence"] >= 0.6 and orders_last_hour >= 10:
            suspicious.append(
                {
                    "code": "too_perfect",
                    "detail": f"{act['detail']} ({orders_last_hour} orders in the last hour)",
                    "confidence": act["confidence"],
                }
            )

        props = gem["propsSuspected"]
        if props["suspected"] and props["confidence"] >= 0.6:
            suspicious.append({"code": "props_suspected", "detail": props["detail"], "confidence": props["confidence"]})

    repeated = repeated_props(observed_items, item_history)
    if repeated:
        suspicious.append(
            {
                "code": "repeated_props",
                "detail": "Same unopened item seen in 3+ audits: " + ", ".join(repeated),
                "confidence": 0.9,
            }
        )

    expected = planned_items * SECONDS_PER_ITEM
    if duration_sec is not None and expected and duration_sec < 0.3 * expected:
        suspicious.append(
            {
                "code": "too_fast",
                "detail": f"Finished in {round(duration_sec)} s; about {expected} s expected",
                "confidence": 0.8,
            }
        )

    result = "failed" if failed else "suspicious" if suspicious else "clean"
    return {"verdict": result, "flags": failed + suspicious + info}
