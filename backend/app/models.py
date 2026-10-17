"""Pydantic models: API request bodies and Gemini structured-output schemas (§11, §12)."""

from typing import Literal

from pydantic import BaseModel, Field

Trigger = Literal["surprise", "customer", "practice"]

# ---------- API bodies ----------


class CreateAuditBody(BaseModel):
    restaurantId: str
    trigger: Trigger
    orderId: str | None = None
    customerId: str | None = None


class Gps(BaseModel):
    lat: float
    lng: float
    accuracy: float | None = None


class StartBody(BaseModel):
    gps: Gps | None = None


class AdvanceBody(BaseModel):
    offsetSec: float = Field(ge=0)
    # index of the item the client is leaving; guards against double taps
    fromIndex: int | None = None


class CompleteBody(BaseModel):
    videoPath: str
    videoMime: str = "video/webm"
    durationSec: float = Field(ge=0)


class DemoSampleBody(BaseModel):
    sample: Literal["messy", "clean", "too_perfect"]


class DisputeBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ReviewBody(BaseModel):
    # dispute items: upheld | overturned. integrity items: clear | confirm_failed
    decision: Literal["upheld", "overturned", "clear", "confirm_failed"]
    by: str = "inspector"


class SurpriseBody(BaseModel):
    restaurantId: str | None = None


class InspectorVisitBody(BaseModel):
    restaurantId: str
    outcome: Literal["confirmed", "contradicts"] = "confirmed"


class DemoOrderBody(BaseModel):
    restaurantId: str
    customerId: str


# ---------- Gemini response schemas ----------


class AuditorFinding(BaseModel):
    checkId: str
    status: Literal["pass", "fail", "not_verified"]
    reason: str
    timestamp: str
    confidence: float


class LivenessObservation(BaseModel):
    observed: str
    fingersCounted: int
    nearObject: str
    timestamp: str
    confidence: float


class ObservedItem(BaseModel):
    label: str
    batchOrExpiry: str
    state: Literal["unopened", "opened", "unclear"]


class EvidenceClip(BaseModel):
    checkId: str
    startSec: float
    endSec: float


class AuditorResult(BaseModel):
    findings: list[AuditorFinding]
    liveness: LivenessObservation
    observedItems: list[ObservedItem]
    evidenceClips: list[EvidenceClip]


class OkSignal(BaseModel):
    ok: bool
    detail: str
    confidence: float


class PropsSignal(BaseModel):
    suspected: bool
    detail: str
    confidence: float


class IntegrityResult(BaseModel):
    continuousTake: OkSignal
    sameKitchenAsReference: OkSignal
    activityMatchesOrders: OkSignal
    propsSuspected: PropsSignal
    kitchenSummary: str


# Coach output uses the key "or" (a Python keyword), so its schema is a plain dict.
COACH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        lang: {"type": "ARRAY", "items": {"type": "STRING"}} for lang in ("en", "hi", "or")
    },
    "required": ["en", "hi", "or"],
}
