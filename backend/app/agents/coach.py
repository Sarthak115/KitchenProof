"""Coach agent (Gemini, text only): short fix list in English, Hindi and Odia (§12.3)."""

from __future__ import annotations

import logging

from .. import checks as C
from .. import gemini
from ..models import COACH_SCHEMA
from ._prompts import fill, load

log = logging.getLogger(__name__)


def build_prompt(findings: list[dict]) -> str:
    lines = []
    for f in findings:
        check = C.CHECKS[f["checkId"]]
        label = "FAILED" if f["status"] == "fail" else "NOT VERIFIED"
        lines.append(f"- {label} {f['checkId']} ({check.severity}): {check.verify}. Seen: {f['reason']}")
    return fill(load("coach"), issues_block="\n".join(lines))


def fallback(findings: list[dict]) -> dict:
    """Offline fix list from the check pool (English only, used if Gemini is unavailable)."""
    steps = []
    for f in findings:
        if f["status"] == "fail":
            steps.append(C.CHECKS[f["checkId"]].fix)
        else:
            steps.append(f"Next time, show this clearly: {C.prompt_for(f['checkId']).lower()}.")
    return {"en": steps[:5], "hi": [], "or": []}


def run(findings: list[dict]) -> dict:
    issues = sorted(
        [f for f in findings if f["status"] in ("fail", "not_verified")],
        key=lambda f: (f["status"] != "fail", C.SEVERITY_ORDER[C.CHECKS[f["checkId"]].severity]),
    )
    if not issues:
        return {"en": ["Great job — keep doing what you are doing."], "hi": [], "or": []}
    if not gemini.available():
        return fallback(issues)
    try:
        result, _ = gemini.generate_json(build_prompt(issues), COACH_SCHEMA)
        return {lang: [str(s) for s in result.get(lang, [])][:5] for lang in ("en", "hi", "or")}
    except Exception as err:  # noqa: BLE001
        log.warning("Coach failed, using fallback: %s", err)
        return fallback(issues)
