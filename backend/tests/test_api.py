from fastapi.testclient import TestClient

from app.demo import seed as demo_seed
from app.main import app


def client(store):
    demo_seed.seed(store)
    return TestClient(app)


def test_seed_has_varied_data(store):
    c = client(store)
    rests = c.get("/api/restaurants").json()["restaurants"]
    assert len(rests) == 15
    tiers = {r["tier"] for r in rests}
    assert {"bronze", "silver", "gold"} <= tiers
    states = {r["badgeState"] for r in rests}
    assert {"scored", "failed_verification", "not_recently_verified", "unverified"} <= states
    queue = c.get("/api/review").json()["items"]
    assert sum(q["type"] == "dispute" for q in queue) == 2
    assert sum(q["type"] == "integrity" for q in queue) == 2
    ranking = c.get("/api/risk/ranking").json()["restaurants"]
    assert ranking[0]["riskScore"] >= ranking[-1]["riskScore"]
    assert all(r["riskReasons"] is not None for r in ranking)


def test_live_audit_flow_hides_plan_and_reveals_in_order(store):
    c = client(store)
    r = c.post("/api/inspector/surprise", json={"restaurantId": "r02"}).json()
    aid = r["auditId"]
    audit = c.get(f"/api/audits/{aid}").json()
    assert "plannedChecks" not in audit and audit["revealedChecks"] == []
    start = c.post(f"/api/audits/{aid}/start", json={"gps": {"lat": 20.2376, "lng": 85.8338}}).json()
    seen = [start["instruction"]]
    idx = 0
    while True:
        res = c.post(f"/api/audits/{aid}/advance", json={"offsetSec": 20 * (idx + 1), "fromIndex": idx}).json()
        if res["done"]:
            break
        seen.append(res["instruction"])
        idx += 1
    kinds = [s["kind"] for s in seen]
    assert kinds.count("liveness") == 1 and kinds.count("check") == 6
    assert any(s.get("checkId") == "order_prep" for s in seen)  # r02 has an active order
    audit = c.get(f"/api/audits/{aid}").json()
    assert len(audit["revealedChecks"]) == 6 and audit["liveness"]["prompt"].startswith("Hold up")
    assert audit["distanceFromRegisteredM"] == 0


def test_duplicate_advance_is_ignored(store):
    c = client(store)
    aid = c.post("/api/inspector/surprise", json={"restaurantId": "r02"}).json()["auditId"]
    c.post(f"/api/audits/{aid}/start", json={})
    a = c.post(f"/api/audits/{aid}/advance", json={"offsetSec": 10, "fromIndex": 0}).json()
    b = c.post(f"/api/audits/{aid}/advance", json={"offsetSec": 11, "fromIndex": 0}).json()
    assert a["instruction"] == b["instruction"]


def test_demo_sample_story(store):
    c = client(store)
    before = c.get("/api/restaurants/r01").json()
    assert before["tier"] == "bronze"

    # surprise audit, messy kitchen -> low score with timestamped evidence (cached result offline)
    aid = c.post("/api/inspector/surprise", json={"restaurantId": "r01"}).json()["auditId"]
    assert c.post(f"/api/audits/{aid}/demo-sample", json={"sample": "messy"}).status_code == 200
    report = c.get(f"/api/audits/{aid}").json()
    # cached result = gemini-3.8-flash's real output on the team's messy video
    assert report["status"] == "scored" and report["score"] == 31 and report["usedCachedResult"]
    assert report["integrity"]["verdict"] == "clean"
    assert report["findings"][0]["checkId"] == "fridge_segregation"
    assert all(f["timestamp"] for f in report["findings"])

    # customer requests a check during their order -> clean kitchen -> silver
    oid = c.post("/api/demo/order", json={"restaurantId": "r01", "customerId": "cust-1"}).json()["orderId"]
    res = c.post("/api/audits", json={"restaurantId": "r01", "trigger": "customer", "orderId": oid, "customerId": "cust-1"})
    assert res.status_code == 200
    aid2 = res.json()["auditId"]
    c.post(f"/api/audits/{aid2}/demo-sample", json={"sample": "clean"})
    order = c.get(f"/api/orders/{oid}").json()
    assert order["spotCheck"]["score"] == c.get(f"/api/audits/{aid2}").json()["score"]
    assert order["spotCheck"]["status"] == "scored" and order["spotCheck"]["score"] == 92
    after = c.get("/api/restaurants/r01").json()
    assert after["tier"] == "silver"  # two passed surprise/customer checks in 30 days
    assert after["evidenceClips"]

    # same customer cannot request again within 7 days
    oid2 = c.post("/api/demo/order", json={"restaurantId": "r01", "customerId": "cust-1"}).json()["orderId"]
    again = c.post("/api/audits", json={"restaurantId": "r01", "trigger": "customer", "orderId": oid2, "customerId": "cust-1"})
    assert again.status_code == 429

    # too-perfect kitchen during a busy hour -> suspicious, excluded, queued
    aid3 = c.post("/api/inspector/surprise", json={"restaurantId": "r01"}).json()["auditId"]
    c.post(f"/api/audits/{aid3}/demo-sample", json={"sample": "too_perfect"})
    tp = c.get(f"/api/audits/{aid3}").json()
    assert tp["integrity"]["verdict"] == "suspicious" and not tp["counted"]
    assert tp["status"] == "under_review"
    codes = {f["code"] for f in tp["integrity"]["flags"]}
    assert "too_perfect" in codes


def test_dispute_then_review(store):
    c = client(store)
    aid = c.post("/api/inspector/surprise", json={"restaurantId": "r01"}).json()["auditId"]
    c.post(f"/api/audits/{aid}/demo-sample", json={"sample": "messy"})
    res = c.post(f"/api/findings/{aid}/dustbins/dispute", json={"reason": "Lid was off only while emptying"})
    assert res.status_code == 200
    audit = res.json()
    assert audit["status"] == "under_review"
    item = next(q for q in c.get("/api/review").json()["items"] if q["auditId"] == aid)
    done = c.post(f"/api/review/{item['id']}", json={"decision": "overturned"}).json()
    assert done["status"] == "resolved"
    assert next(f for f in done["findings"] if f["checkId"] == "dustbins")["effectiveStatus"] == "pass"


def test_customer_rules(store):
    c = client(store)
    # someone else's order
    res = c.post("/api/audits", json={"restaurantId": "r01", "trigger": "customer", "orderId": "4521", "customerId": "intruder"})
    assert res.status_code == 403
    # owner cannot fake a surprise audit
    assert c.post("/api/audits", json={"restaurantId": "r01", "trigger": "surprise"}).status_code == 400


def test_missed_check_on_expiry(store):
    from datetime import timedelta

    from app.timeutil import utcnow

    c = client(store)
    aid = c.post("/api/inspector/surprise", json={"restaurantId": "r02"}).json()["auditId"]
    store.update("audits", aid, {"startDeadlineAt": utcnow() - timedelta(minutes=1)})
    assert c.post(f"/api/audits/{aid}/start", json={}).status_code == 410
    assert c.get(f"/api/audits/{aid}").json()["status"] == "expired"
    assert c.get("/api/restaurants/r02").json()["missedChecks30d"] == 1


def test_health(store):
    c = client(store)
    assert c.get("/api/health").json()["ok"]


def test_reaudit_for_inconclusive(store):
    c = client(store)
    aid = c.post("/api/inspector/surprise", json={"restaurantId": "r02"}).json()["auditId"]
    store.update("audits", aid, {"status": "inconclusive", "outcome": "inconclusive"})
    from app.timeutil import utcnow

    store.update("audits", aid, {"completedAt": utcnow()})
    res = c.post(f"/api/audits/{aid}/reaudit").json()
    assert res["auditId"] != aid
    assert c.get(f"/api/audits/{res['auditId']}").json()["trigger"] == "surprise"
    assert c.post(f"/api/audits/{aid}/reaudit").json()["auditId"] == res["auditId"]


def test_demo_kitchen_uses_its_check_profile(store):
    c = client(store)
    aid = c.post("/api/inspector/surprise", json={"restaurantId": "r01"}).json()["auditId"]
    first = c.post(f"/api/audits/{aid}/start", json={}).json()["instruction"]
    seen = [first]
    idx = 0
    while True:
        res = c.post(f"/api/audits/{aid}/advance", json={"offsetSec": 10 * (idx + 1), "fromIndex": idx}).json()
        if res["done"]:
            break
        seen.append(res["instruction"])
        idx += 1
    checks = {s["checkId"] for s in seen if s["kind"] == "check"}
    assert checks == set(demo_seed.HERO_CHECK_PROFILE)
    gesture = next(s for s in seen if s["kind"] == "liveness")["prompt"]
    assert any(o in gesture for o in demo_seed.HERO_LIVENESS_OBJECTS)
