"""Auditor agent (Gemini): scores the recording per check with timestamped evidence (§12.1)."""

from __future__ import annotations

from .. import checks as C
from .. import gemini
from ..models import AuditorResult
from ..timeutil import utcnow, IST
from ._prompts import fill, load


def build_prompt(check_ids: list[str], timeline: list[dict], liveness: dict | None, order_id: str | None) -> str:
    checks_block = "\n".join(f"- {cid}: {C.CHECKS[cid].verify}" for cid in check_ids)
    timeline_block = "\n".join(
        f"- {round(item['offsetSec'])}s: [{item['checkId']}] \"{item['prompt']}\"" for item in timeline
    )
    return fill(
        load("auditor"),
        checks_block=checks_block,
        timeline_block=timeline_block or "- (no timeline recorded)",
        liveness_offset=round((liveness or {}).get("offsetSec") or 0),
        liveness_prompt=(liveness or {}).get("prompt", "none"),
        today=utcnow().astimezone(IST).date().isoformat(),
    )


def run(video, check_ids: list[str], timeline: list[dict], liveness: dict | None, order_id: str | None) -> tuple[dict, str]:
    prompt = build_prompt(check_ids, timeline, liveness, order_id)
    result, model_id = gemini.generate_json(prompt, AuditorResult, video=video)
    return normalize(result, check_ids), model_id


def normalize(result: dict, check_ids: list[str]) -> dict:
    """Validate Gemini output; keep exactly one finding per requested check."""
    parsed = AuditorResult.model_validate(result).model_dump()
    by_id = {}
    for f in parsed["findings"]:
        if f["checkId"] in check_ids and f["checkId"] not in by_id:
            f["confidence"] = max(0.0, min(1.0, float(f["confidence"])))
            by_id[f["checkId"]] = f
    for cid in check_ids:
        by_id.setdefault(
            cid,
            {
                "checkId": cid,
                "status": "not_verified",
                "reason": "Not shown clearly in the video.",
                "timestamp": "00:00",
                "confidence": 0.0,
            },
        )
    parsed["findings"] = [by_id[cid] for cid in check_ids]
    parsed["evidenceClips"] = [
        c for c in parsed["evidenceClips"] if c["checkId"] in check_ids and c["endSec"] > c["startSec"]
    ]
    return parsed
