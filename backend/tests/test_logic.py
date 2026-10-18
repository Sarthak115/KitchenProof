import random
from datetime import timedelta

from app import checks as C
from app.agents import integrity, planner, risk, scorer
from app.timeutil import utcnow


def test_pick_checks_mix_and_order_prep():
    rng = random.Random(1)
    for _ in range(200):
        ids = planner.pick_checks(rng, has_active_order=True)
        sev = [C.CHECKS[c].severity for c in ids]
        assert len(ids) == 6 and len(set(ids)) == 6
        assert 1 <= sev.count("critical") <= 2
        assert 2 <= sev.count("high") <= 3
        assert "order_prep" in ids


def test_pick_checks_never_repeats_previous_set():
    rng = random.Random(2)
    prev = planner.pick_checks(rng, False)
    for _ in range(50):
        assert set(planner.pick_checks(rng, False, prev)) != set(prev)


def test_liveness_between_checks_2_and_5():
    rng = random.Random(3)
    for _ in range(100):
        seq = planner.build_sequence(rng, ["a", "b", "c", "d", "e", "f"])
        pos = [s["kind"] for s in seq].index("liveness")
        assert pos in (2, 3, 4)


def f(cid, status, conf=0.9, **kw):
    return {"checkId": cid, "status": status, "confidence": conf, "reason": "", "timestamp": "00:01", **kw}


def test_score_penalties_and_critical_cap():
    findings = [f("pests", "fail", 0.85), f("handwash", "pass"), f("dustbins", "fail"),
                f("surfaces", "pass"), f("drains", "pass"), f("fssai_board", "pass")]
    r = scorer.score_audit(findings, 6, "clean", "surprise")
    assert r["score"] == 40  # 100-30-8=62, capped at 40
    assert r["status"] == "scored" and r["counted"]


def test_low_confidence_critical_goes_to_review_not_penalty():
    findings = [f("pests", "fail", 0.7), f("handwash", "pass"), f("dustbins", "pass"),
                f("surfaces", "pass"), f("drains", "pass"), f("fssai_board", "pass"), f("water_source", "pass")]
    r = scorer.score_audit(findings, 7, "clean", "surprise")
    assert r["score"] == 100
    assert r["findings"][0]["needsReview"] and not r["findings"][0]["publicEligible"]
    assert r["coverage"] == round(6 / 7, 3)


def test_not_verified_lowers_coverage_not_score():
    findings = [f("pests", "pass"), f("handwash", "not_verified", 0.2), f("dustbins", "not_verified", 0.2),
                f("surfaces", "pass"), f("drains", "pass"), f("fssai_board", "pass")]
    r = scorer.score_audit(findings, 6, "clean", "customer")
    assert r["score"] == 100
    assert r["status"] == "inconclusive" and not r["counted"]


def test_disputed_and_overturned():
    findings = [f("dustbins", "fail", disputed=True), f("pests", "pass"), f("handwash", "pass"),
                f("surfaces", "pass"), f("drains", "pass"), f("fssai_board", "pass")]
    assert scorer.score_audit(findings, 6, "clean", "surprise")["score"] == 100
    findings[0]["review"] = {"decision": "upheld"}
    assert scorer.score_audit(findings, 6, "clean", "surprise")["score"] == 92
    findings[0]["review"] = {"decision": "overturned"}
    assert scorer.score_audit(findings, 6, "clean", "surprise")["score"] == 100


def test_integrity_outcomes():
    findings = [f("pests", "pass"), f("handwash", "pass"), f("dustbins", "pass"),
                f("surfaces", "pass"), f("drains", "pass"), f("fssai_board", "pass")]
    failed = scorer.score_audit(findings, 6, "failed", "surprise")
    assert failed["score"] == 0 and failed["counted"]
    sus = scorer.score_audit(findings, 6, "suspicious", "surprise")
    assert not sus["counted"] and sus["status"] == "flagged"
    practice = scorer.score_audit(findings, 6, "clean", "practice")
    assert not practice["counted"]


def test_public_score_decay():
    now = utcnow()
    audits = [{"score": 80, "completedAt": now - timedelta(days=45)}]
    assert scorer.public_score(audits, now)["publicScore"] == 70  # 2 full weeks beyond 30 days
    audits = [{"score": 80, "completedAt": now - timedelta(days=61)}]
    assert scorer.public_score(audits, now)["notRecentlyVerified"]
    audits = [{"score": 60, "completedAt": now - timedelta(days=3)},
              {"score": 90, "completedAt": now - timedelta(days=1), "inspectorConfirmed": True}]
    assert scorer.public_score(audits, now)["publicScore"] == 78  # (60 + 135) / 2.5


def test_tiers():
    now = utcnow()
    good = lambda d, t="surprise": {"trigger": t, "counted": True, "score": 85, "completedAt": now - timedelta(days=d), "integrity": {"verdict": "clean"}}  # noqa: E731
    assert scorer.tier([good(3, "practice")], None, now) == "bronze"
    assert scorer.tier([good(3), good(10, "customer")], None, now) == "silver"
    assert scorer.tier([good(3), good(10)], now - timedelta(days=20), now) == "gold"
    bad = {**good(5), "integrity": {"verdict": "failed"}}
    assert scorer.tier([good(3), good(10), bad], now, now) == "bronze"


def test_risk_reasons():
    score, reasons = risk.compute(public_score=52, missed_checks_30d=2, integrity_issue_30d=True,
                                  open_disputes=1, score_drop=32, no_counted_audit_30d=False)
    assert score == 24 + 30 + 20 + 10 + 10
    assert "2 missed checks this month" in reasons
    assert "Score fell 32 points since last audit" in reasons


def sig(ok=True, conf=0.9):
    return {"ok": ok, "detail": "x", "confidence": conf}


def base_gem(**kw):
    g = {"continuousTake": sig(), "sameKitchenAsReference": sig(), "activityMatchesOrders": sig(),
         "propsSuspected": {"suspected": False, "detail": "", "confidence": 0.9}}
    g.update(kw)
    return g


def verdict(**kw):
    args = dict(gem=base_gem(), liveness_obs={"fingersCounted": 3, "nearObject": "gas stove", "confidence": 0.9, "observed": ""},
                liveness_expected={"n": 3, "object": "stove"}, distance_m=20, orders_last_hour=12,
                has_reference=True, observed_items=[], item_history=[], duration_sec=140, planned_items=7)
    args.update(kw)
    return integrity.verdict(**args)["verdict"]


def test_integrity_rules():
    assert verdict() == "clean"
    assert verdict(liveness_obs={"fingersCounted": 2, "nearObject": "stove", "confidence": 0.8, "observed": ""}) == "failed"
    assert verdict(liveness_obs={"fingersCounted": 2, "nearObject": "stove", "confidence": 0.5, "observed": ""}) == "clean"
    assert verdict(distance_m=900) == "failed"
    assert verdict(gem=base_gem(continuousTake=sig(False, 0.85))) == "failed"
    assert verdict(gem=base_gem(activityMatchesOrders=sig(False, 0.8))) == "suspicious"
    assert verdict(gem=base_gem(activityMatchesOrders=sig(False, 0.8)), orders_last_hour=3) == "clean"
    assert verdict(gem=base_gem(sameKitchenAsReference=sig(False, 0.7)), has_reference=False) == "clean"
    assert verdict(duration_sec=30) == "suspicious"
    item = {"label": "Oil", "batchOrExpiry": "B1", "state": "unopened"}
    assert verdict(observed_items=[item], item_history=[[item], [item]]) == "suspicious"
    assert verdict(observed_items=[item], item_history=[[item]]) == "clean"


def test_clamp_clips_inside_video():
    from app.agents.orchestrator import clamp_clips

    clips = [{"checkId": "a", "startSec": 120, "endSec": 124}, {"checkId": "b", "startSec": 5, "endSec": 9}]
    out = clamp_clips(clips, 93)
    assert out[0] == {"checkId": "a", "startSec": 90, "endSec": 93}
    assert out[1] == clips[1]


def test_gemini_client_created_once_across_threads(monkeypatch):
    """Parallel auditor + integrity calls must share one client (a replaced client gets closed)."""
    import sys
    import threading
    import time
    import types

    from app import gemini

    created = []

    class FakeClient:
        def __init__(self, **kw):
            time.sleep(0.05)  # widen the race window
            created.append(self)

    fake = types.ModuleType("google.genai")
    fake.Client = FakeClient
    monkeypatch.setitem(sys.modules, "google.genai", fake)
    import google

    monkeypatch.setattr(google, "genai", fake, raising=False)
    monkeypatch.setattr(gemini, "_client", None)
    monkeypatch.setattr(gemini, "available", lambda: True)

    got = []
    threads = [threading.Thread(target=lambda: got.append(gemini.client())) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(created) == 1 and all(c is created[0] for c in got)


def test_check_profile_limits_checks_and_gesture_objects():
    from app.liveness import make_challenge

    rng = random.Random(7)
    profile = ["fridge_segregation", "handwash", "dustbins", "surfaces", "dry_storage", "labels_expiry"]
    orders = set()
    for _ in range(30):
        ids = planner.pick_checks(rng, has_active_order=True, allowed=profile)
        assert sorted(ids) == sorted(profile)  # only what the kitchen has; no order_prep
        orders.add(tuple(ids))
        assert make_challenge(rng, ["stove", "fridge"])["object"] in ("stove", "fridge")
    assert len(orders) > 1  # order is still random

    big = list(C.CHECKS)[:12]
    for _ in range(30):
        ids = planner.pick_checks(rng, has_active_order=False, allowed=big)
        assert len(ids) == 6 and set(ids) <= set(big)
