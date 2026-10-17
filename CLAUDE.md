# KitchenProof — Build Spec for Claude Code

> Hand this whole file to Claude Code (or save it as `CLAUDE.md` in the repo root). It is the single source of truth for what to build, how, and how to deploy it so it meets the Google Cloud AI Builder Cup 2026 rules.

---

## 0. Instructions to Claude Code (read first)

- **Deadline is hard.** Submission is due before 18 October 2026. The team wants to submit by **midday 18 Oct IST**. Build in the phase order in §13 and keep the app deployable after every phase.
- **Prototype, not product.** Prefer simple, working code over abstractions. No microservices beyond the two listed (web app + one API service).
- **Do not change the stack** in §8 without asking. Every listed Google product is there to satisfy the competition rules.
- **Phase 0 first:** build and run `scripts/test_auditor.py` (§13) before anything else. If Gemini cannot detect the obvious problems in the team's test videos, stop and report.
- **Keep the app judge-proof:** a judge must be able to open the deployed link on a laptop or phone, with no setup or login, and see the full story in Demo Mode (§7.6).
- **English only** in code, UI default language, README and comments (rule). Hindi/Odia are optional extras for fix lists and prompts.
- Never call real brands (Zomato, Swiggy, FSSAI) partners. The food app mockup is a made-up brand: **"FoodieGo"**. The score is labelled **"Self-audit verified by AI — not an official FSSAI rating."**

---

## 1. Competition rules this build must satisfy

Source: aibuildercup.com themes page and FAQ (checked 17 Oct 2026).

| Rule | How this build satisfies it |
|---|---|
| Must use Google AI models (Gemini/Gemma) or Google agentic platforms | Gemini (latest Flash model) via the Google Gen AI SDK on **Vertex AI / Gemini Enterprise Agent Platform**; agents structured as modules (optionally ADK, §8) |
| Must be deployed on Google Cloud via **Cloud Run or Firebase** | Web app on **Firebase Hosting**; API on **Cloud Run**; data in **Firestore**; videos in **Cloud Storage for Firebase** |
| Working prototype, end to end | Live audit → Gemini scoring → public badge → inspector ranking all work in the deployed app |
| Submission: **working deployed link**, **public GitHub repo**, **demo video under 3 minutes** (public YouTube/Vimeo/Drive), **deck as PDF** | §12 checklist |
| Only fresh projects built during the hackathon | New repo; commit early and often so history shows the timeline |
| All materials in English | Yes |
| One solution, one theme | Theme: **Retail & Commerce — Intelligent Customer and Business Experiences** (customer trust + fraud) |

**Judging weights (design for these):** Technical Merit & Gen AI 40% · Problem Alignment & Impact 25% · Innovation & Creativity 25% · UX & Design 10%. Bonus prizes include **Best UI/UX** and **Best use of Google Cloud AI tools**.

---

## 2. Product in one paragraph

Since Maharashtra FDA Commissioner Tukaram Mundhe took charge in May 2026, thousands of raids have exposed cockroaches, rats and rotting food in well-known kitchens, while experts say inspections alone can't fix the problem because there are too few inspectors. Customers ordering online never see the kitchen. **KitchenProof** is a phone-based, AI-guided kitchen audit. At unpredictable moments (a surprise from the platform, or a customer's request during their order), the restaurant must do a short live camera walk-through. The app reveals randomly chosen checks one at a time ("show the inside of your fridge", "show order #4521 being prepared now", "hold up three fingers next to the stove"). Gemini scores the recording against FSSAI-style hygiene checks with timestamped evidence, and a separate integrity check looks for staging. Customers see a verified **Kitchen Score** with an **evidence tier**; inspectors get a ranked list of kitchens to visit first.

**Pitch line:** *"We can't stop someone faking one video. KitchenProof makes faking it every day, at random times, while real orders are cooking, harder than just keeping the kitchen clean."*

---

## 3. Users and what each sees

| User | Main job | Key screens |
|---|---|---|
| **Restaurant owner** | Respond to audit requests; fix problems; dispute wrong findings | Owner dashboard, Live Audit, Audit Report |
| **Customer** (FoodieGo mockup) | Choose a trustworthy kitchen; request a check during their own order | Restaurant list with badges, Restaurant page, Order page with "Request kitchen check" |
| **Food safety inspector** | Decide where to inspect; review disputes and staging flags | Risk ranking, Restaurant detail, Review queue |

---

## 4. Final feature list

### 4.1 MUST (core — never cut)
1. **Audit requests with three triggers:** `surprise` (platform, random time), `customer` (customer request during a live order), `practice` (owner-initiated; never counts toward the public score).
2. **Live Audit flow** (in-app camera only): server-chosen checks revealed one at a time, a liveness challenge, continuous recording, upload to Cloud Storage.
3. **Auditor (Gemini):** scores the recording per check → `pass | fail | not_verified`, severity, reason, MM:SS timestamp, confidence.
4. **Integrity check (Gemini + rules):** liveness verified, continuous take, scene matches the kitchen's reference audit, too-perfect vs order volume, repeated props, response timing → `clean | suspicious | failed`.
5. **Scoring + evidence tier + decay** (deterministic code, §6.4).
6. **Audit Report** with evidence thumbnails that jump to the timestamp in the video, and a **Dispute** button per finding.
7. **Customer badge** on FoodieGo: score, tier, last verified, missed checks, 3 evidence clips.
8. **Customer-requested spot check** with result shown back on the customer's order page.
9. **Inspector risk ranking** with plain-language reasons + **review queue** for disputes and staging flags.
10. **Demo Mode** for judges with seeded data and real Gemini analysis on sample videos (§7.6).

### 4.2 SHOULD (if time allows, in this order)
11. **Coach (Gemini):** fix list in English, plus Hindi/Odia toggle.
12. **Prompts read aloud** with the browser's `speechSynthesis` (EN/HI).
13. Simple **map** on the inspector screen (Google Maps JavaScript API).
14. **Cloud Scheduler** job that triggers real surprise audits (demo uses a button instead).

### 4.3 STRETCH (only if everything above is done and deployed)
15. **Gemini Live voice guide** (Firebase AI Logic Live API) replacing text prompts.
16. Port the agent orchestration to **ADK**.
17. Delivery-rider pickup photo checks (show as "Roadmap" in UI/deck only).

### 4.4 OUT OF SCOPE (mention as roadmap in the deck)
Real FoodieGo/FSSAI integrations, rider app, push notifications (FCM), lab testing, payments.

---

## 5. Anti-fake and anti-false design (the core differentiator)

Judges **will** ask: *"Can't the owner stage it?"* and *"What if the AI is wrong?"* This section answers both and must be visible in the product, not just the deck.

### 5.1 Stopping owners from faking (staging)

| # | Defence | Implementation |
|---|---|---|
| 1 | **Unpredictable timing** | Owner never chooses when a counted audit happens. `surprise` audits are created by the server at random times weighted to peak hours (12:00–15:00, 19:00–23:00 IST). `customer` audits come from real orders. |
| 2 | **Short response window** | Audit must be **started within 10 minutes** of the request and **finished within 4 minutes** of starting. Missing the window = **missed check** (shown publicly on the badge, raises risk). |
| 3 | **Checks revealed one at a time** | Server picks 6 checks at random from the pool (§6.2), always including ≥1 critical check. Client calls `/advance` to get the next one; the server logs when each was revealed. The owner cannot see the list in advance. |
| 4 | **Real-order check** | If the restaurant has an active order (always true for `customer` audits), one check is *"Show order #XXXX being prepared right now"*. Proves this is the live working kitchen. |
| 5 | **Liveness challenge** | At a random point the app shows a random gesture: *"Hold up {N} fingers in front of the {object}"* (N 1–5, object from stove/fridge/sink). Gemini must confirm it at the right time. Defeats pre-recorded or replayed video. |
| 6 | **In-app continuous capture only** | `getUserMedia` + `MediaRecorder`; no gallery upload in real mode. Integrity check flags cuts, jumps, sudden lighting/room changes. |
| 7 | **Location + server time** | GPS captured at start; must be within 200 m of the registered address (else flag). All times are server timestamps. |
| 8 | **Scene consistency** | Each restaurant has a **reference audit** (first verified audit). Integrity check compares layout, tiles, equipment; a different-looking kitchen is flagged. |
| 9 | **Too-perfect check** | Integrity prompt receives the order count for the last hour. A spotless, empty, inactive kitchen during a busy hour is flagged as *possibly staged*. |
| 10 | **Repeated props** | Auditor extracts visible labels/batch/expiry text into `observedItems`. If the same item (same batch, same fill level, unopened) appears across ≥3 audits, flag *possible prop*. |
| 11 | **Evidence tier on the badge** | 🥉 **Bronze** = only practice/self audits · 🥈 **Silver** = ≥2 surprise or customer audits passed in the last 30 days, no failed integrity · 🥇 **Gold** = Silver + an inspector visit recorded (seeded in demo). A staged one-off video can never exceed Bronze. |
| 12 | **Inspector outweighs self-audit** | If an inspector review contradicts an audit, the audit is voided and the badge shows **"Failed verification"** for 30 days. This makes cheating not worth it. |
| 13 | **Decay** | Score fades if no verified audit in 30 days (§6.4). |

### 5.2 Protecting owners from false AI findings (fairness)

| # | Safeguard | Implementation |
|---|---|---|
| 1 | **"Not verified" is not "fail"** | If a check wasn't shown clearly, Gemini must return `not_verified`. It lowers coverage, never the score. |
| 2 | **Confidence gates** | Findings with confidence < 0.6 are `needs_review` and **never public**. A critical fail needs confidence ≥ 0.8 to cap the score; otherwise it goes to review. |
| 3 | **Evidence for every finding** | Every finding has a timestamp; the report shows the clip at that moment. No evidence → no penalty. |
| 4 | **Coverage rule** | If < 70% of requested checks are verified, the audit is **inconclusive**: not counted publicly, owner gets a quick re-audit. |
| 5 | **Dispute → human review** | Owner can dispute any finding with a reason. Disputed findings are hidden from the public score until an inspector decides. |
| 6 | **Integrity "suspicious" ≠ guilty** | Suspicious audits are excluded from the public score and queued for review; the public sees only "under review". Only `failed` integrity (e.g. liveness failed, wrong location) is shown publicly. |
| 7 | **Careful wording** | Public UI never says "unsafe" or "dirty". It says "Kitchen Score 52 · 2 issues found · verified 3 days ago". Disclaimer on every badge. |
| 8 | **Model + prompt version logged** | Each audit stores model ID and prompt version for traceability. |

### 5.3 Stopping customers from abusing spot checks
- Only a customer with an **active order** at that restaurant can request one.
- Limits: **1 request per customer per restaurant per 7 days**, **max 3 customer checks per restaurant per day**.
- The customer sees the result, not the raw video (privacy), plus up to 3 short evidence clips the restaurant has made public.

### 5.4 Privacy
- Owner is told to keep faces out of frame; Gemini is instructed **never to identify people**, only hygiene items (hairnet, gloves, apron).
- Public evidence clips are 3–5 second segments of surfaces/equipment chosen from passing checks.
- Raw videos are not public; retained only for review (state "deleted after 90 days" as policy in UI).

---

## 6. Domain logic

### 6.1 Audit lifecycle

```
requested → in_progress → uploaded → analyzing → scored | inconclusive | flagged
requested → expired           (not started within 10 min = missed check)
in_progress → expired         (not finished within 4 min)
scored/flagged → under_review → resolved   (dispute or integrity flag)
```

### 6.2 Check pool (FSSAI Hygiene Rating–style, camera-verifiable)

Store as `backend/app/checks.py` (and mirror IDs in the frontend for labels).

| id | Prompt shown to owner | What Gemini verifies | Severity |
|---|---|---|---|
| `pests` | Show the floor under the stove and the corners of the room | No droppings, cockroaches, larvae, rodent signs | critical |
| `fridge_segregation` | Open the fridge and show each shelf slowly | Raw meat/fish not above cooked or ready-to-eat food; veg/non-veg separated; food covered | critical |
| `fridge_temp` | Bring the camera close to the fridge thermometer | Reading visible and ≤ 5 °C | high |
| `handwash` | Show the handwash sink and turn on the tap | Soap present, running water, basin clean | high |
| `handler_hygiene` | Show the person cooking from the shoulders down | Head covering, gloves or clean hands, clean apron (no faces needed) | high |
| `order_prep` | Show order #{orderId} being prepared right now | Active cooking/plating visible; handler hygiene during prep | high |
| `dustbins` | Show your dustbins with their lids | Lid present and closed, not overflowing | medium |
| `surfaces` | Show the cutting boards and the main cooking counter | No visible grime, stains, food residue build-up | medium |
| `drains` | Show the floor drain | Grating present, no standing waste | medium |
| `dry_storage` | Show where you store flour, rice and vegetables | Off the floor on racks, containers/sacks closed | medium |
| `labels_expiry` | Show the labels of two packaged ingredients | Expiry date readable and not past today's date | medium |
| `oil_condition` | Show the frying oil in the kadhai or fryer | Oil not visibly black/foaming (visual only; flag, do not certify) | medium |
| `walls_ceiling` | Slowly show the walls and ceiling above the cooking area | No heavy grease, mould, peeling paint over food areas | low |
| `fssai_board` | Show your FSSAI licence on the wall | Licence/registration visible; number readable | low |
| `pest_control_record` | Show your last pest control certificate | A dated document visible | low |
| `water_source` | Show your drinking-water filter or source | Filter/source present and clean | low |

**Selection rule:** 6 checks per audit = 1–2 critical + 2–3 high + rest medium/low, random each time; `order_prep` always included when there's an active order; never repeat the exact same set twice in a row for a restaurant. Plus **1 liveness challenge** inserted at a random position between checks 2 and 5.

### 6.3 Liveness challenge pool
`"Hold up {n} fingers in front of the {object}"` with n ∈ {1..5}, object ∈ {stove, fridge, sink, gas cylinder}. Store the expected answer server-side only.

### 6.4 Scoring

```
Penalty per FAILED finding (only public-eligible, confidence-gated):
  critical 30 · high 15 · medium 8 · low 4
auditScore = max(0, 100 − Σ penalties)
If any critical fail with confidence ≥ 0.8 → auditScore = min(auditScore, 40)
coverage  = verifiedChecks / requestedChecks   (not_verified and needs_review are unverified)
coverage < 0.70 → status = inconclusive (not counted)
Integrity: failed → audit counts as 0 and badge shows "Failed verification";
           suspicious → excluded, under review
```

**Public Kitchen Score** = weighted average of counted audits in the last 30 days (customer and surprise audits weight 1.0; inspector-confirmed 1.5). **Decay:** for each full week beyond 30 days since the last counted audit, subtract 5 points; after 60 days show "Not recently verified" instead of a number.

**Missed checks:** each expired audit adds to `missedChecks30d` (shown on badge) and +15 to risk.

### 6.5 Inspector risk ranking (deterministic, with reasons)

```
risk = (100 − publicScore) × 0.5
     + 15 × missedChecks30d
     + 20 if any integrity failed/suspicious in 30d
     + 10 × open disputes
     + 10 if score dropped ≥ 20 points since previous audit
     + 15 if no counted audit in 30 days
```
Each term that contributes produces a human-readable reason string ("Score fell 32 points since last audit", "2 missed checks this month"). Optionally one Gemini call writes a 1-sentence summary per restaurant (SHOULD).

---

## 7. Screens (web app routes)

Design: clean, high-contrast, large touch targets, mobile-first for owner/customer, desktop-first for inspector. Use one accent colour (a trustworthy green/teal) and a red/amber/green status scale. Show evidence everywhere — trust comes from seeing the clip.

### 7.1 `/` — Landing / Judge entry
- One-line pitch, 3 big role cards: **Restaurant Owner**, **Customer (FoodieGo)**, **Food Inspector**.
- Prominent **"Start the 2-minute demo tour"** button (§7.6).
- Footer: "Built with Gemini on Google Cloud (Cloud Run, Firebase)".

### 7.2 Owner
- `/owner` dashboard: restaurant name, current Kitchen Score + tier badge, missed checks, **incoming audit request banner with live countdown** (Firestore listener), audit history, "Practice audit" button.
- `/owner/audit/:auditId` **Live Audit**:
  1. Permission screen (camera, mic, location) with privacy note ("keep faces out of frame").
  2. Full-screen camera; top caption shows the current instruction (and reads it aloud if SHOULD #12 done); bottom: progress ("Check 3 of 6"), countdown, big **"Done — next"** button.
  3. Liveness challenge appears as a distinct amber card.
  4. Recording runs continuously from the first check to the last; on finish, upload with progress bar; then "Analyzing… (about a minute)" with live status.
- `/owner/report/:auditId` **Audit Report**: big score + tier, integrity status chip, coverage, findings list (critical first) each with pass/fail/not verified, one-line reason, confidence, **thumbnail → opens video at timestamp**, **Dispute** button; fix list (Coach) with language toggle; "Re-audit" if inconclusive.

### 7.3 Customer (FoodieGo mockup — made-up brand)
- `/customer` restaurant list cards: name, cuisine, rating, **Kitchen Score badge** (score, tier icon, "verified 2d ago", "1 missed check").
- `/customer/restaurant/:id`: badge detail, explanation of tiers, 3 evidence clips, disclaimer, recent audit timeline (dates + outcomes, no raw video).
- `/customer/order/:orderId`: fake active order tracker + **"Request a kitchen check"** button (respect limits §5.3). After request: status card "Kitchen has 10 minutes to respond" → result "✅ Verified during your order · Score 86" or "⚠️ Kitchen didn't respond in time (recorded as a missed check)".

### 7.4 Inspector
- `/inspector` **Visit first this week**: ranked table (rank, restaurant, score, tier, risk, top 2 reasons, flags). Optional map (SHOULD #13).
- `/inspector/restaurant/:id`: audit history, findings, integrity flags, video player.
- `/inspector/review` queue: disputed findings and suspicious audits; buttons **Uphold finding / Overturn finding**, **Clear integrity flag / Confirm failed verification**.
- **"Trigger surprise audit"** control (picks a restaurant or a chosen one) — this is how the demo creates a surprise audit.

### 7.5 Shared components
`ScoreBadge`, `TierIcon`, `IntegrityChip`, `FindingRow`, `EvidencePlayer` (video with seek-to-timestamp), `Countdown`, `StatusTimeline`.

### 7.6 Demo Mode (judge-proof)
- A `DEMO` toggle (on by default for the public link) shows a visible "DEMO DATA" ribbon.
- **Seeded data:** 15 made-up Bhubaneswar restaurants with varied scores, tiers, missed checks, 2 disputes, 1 suspicious and 1 failed-integrity audit, and order counts.
- **Sample videos** (team records and puts in `demo-assets/`): `messy_kitchen.mp4`, `clean_kitchen.mp4`, `too_perfect_kitchen.mp4` (spotless and inactive, used with a high order count). In Demo Mode only, the Live Audit screen offers **"Use sample video"** instead of the camera; the backend runs **real Gemini analysis** on it with a matching prompt timeline.
- **Cached fallback:** store a precomputed result for each sample video; if Gemini errors or quota fails, show the cached result with a small "cached result" note. The demo must never dead-end.
- **Guided tour** (`/tour`): 6 steps with Next buttons: (1) Inspector triggers a surprise audit → (2) Owner sees the countdown → (3) Live audit with sample video → (4) Report with timestamped evidence → (5) Customer badge updates; customer requests a check → (6) Inspector ranking + review queue, including the too-perfect flag.
- Real mode (camera, no sample videos) remains available via the toggle so the team can film the real demo.

---

## 8. Tech stack (final)

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS; PWA via `vite-plugin-pwa` (manifest + icons; installable) |
| Frontend Google SDKs | Firebase JS SDK: Authentication (**anonymous sign-in**), Firestore (realtime listeners), Cloud Storage for Firebase (resumable video upload) |
| Camera/recording | `navigator.mediaDevices.getUserMedia` + `MediaRecorder` (Chrome: `video/webm`; iOS Safari: `video/mp4` — detect with `MediaRecorder.isTypeSupported`). Target 720p, ≤ 4 min |
| Location | `navigator.geolocation` |
| Hosting | **Firebase Hosting** (HTTPS, required for camera/sensors) with rewrite `/api/**` → Cloud Run service |
| Backend | **Python 3.12 + FastAPI** on **Cloud Run** (region `asia-south1`), container built from source (`gcloud run deploy --source`) |
| AI | **Google Gen AI SDK** (`google-genai`) calling **Gemini on Vertex AI** (`vertexai=True`, `location="global"`). Model ID from env `GEMINI_MODEL` — use the newest Gemini Flash available in the project (check Vertex Model Garden / AI Studio; e.g. a `gemini-3.x-flash` ID), fallback `gemini-2.5-flash`. Structured output with `response_mime_type="application/json"` + `response_schema` |
| Video to Gemini | Video is uploaded by the browser to Cloud Storage; backend passes the `gs://` URI with `types.Part.from_uri(file_uri=..., mime_type=...)` (avoids Cloud Run's request-size limit) |
| Data | Firestore (Native mode); backend uses `google-cloud-firestore` / `firebase-admin` |
| Agents | Python modules: `planner`, `auditor`, `integrity`, `coach`, `scorer`, `risk`, orchestrated by `orchestrator.py`. STRETCH: wrap with **ADK** (`google-adk`) keeping the same interfaces |
| Scheduling | Demo: inspector button. SHOULD: **Cloud Scheduler** → `POST /api/scheduler/surprise` with a shared secret header |
| Local dev | `GOOGLE_GENAI_USE_VERTEXAI=true` with `gcloud auth application-default login`, or `GEMINI_API_KEY` for AI Studio as a fallback (then upload video via the Gemini Files API instead of `gs://`) |

---

## 9. Architecture

```
Browser (PWA on Firebase Hosting)
  ├─ Firebase Auth (anonymous)
  ├─ Firestore realtime listeners (audit status, badges, requests)
  ├─ Cloud Storage upload: audits/{auditId}/recording.{webm|mp4}
  └─ /api/**  ──(Firebase Hosting rewrite)──▶  Cloud Run: kitchenproof-api (FastAPI)
                                                 ├─ planner      (random checks + liveness; deterministic)
                                                 ├─ auditor      (Gemini: video + prompt timeline → findings JSON)
                                                 ├─ integrity    (Gemini + rules: staging signals JSON)
                                                 ├─ coach        (Gemini: fix list, EN/HI/OR)
                                                 ├─ scorer/risk  (deterministic scoring, tier, decay, ranking)
                                                 ├─ Firestore (firebase-admin)
                                                 └─ Gemini on Vertex AI (reads gs:// video)
Cloud Scheduler (SHOULD) ──▶ /api/scheduler/surprise
```

Per completed audit, the orchestrator runs: **auditor** and **integrity** in parallel (two Gemini calls on the same `gs://` video) → **scorer** → **coach** (text-only Gemini call) → writes results → **risk** recompute for that restaurant.

---

## 10. Data model (Firestore)

```
restaurants/{restaurantId}
  name, cuisine, address, geo {lat,lng}, fssaiLicense, demo: bool,
  ordersLastHour (int, demo-seeded), publicScore (int|null), tier ("bronze"|"silver"|"gold"),
  lastCountedAuditAt, missedChecks30d, failedVerificationUntil (ts|null),
  referenceAuditId, inspectorVisitAt (ts|null), riskScore, riskReasons [string]

orders/{orderId}
  restaurantId, customerId, items [string], status ("preparing"|"out_for_delivery"|"delivered"),
  createdAt, spotCheckAuditId (optional)

audits/{auditId}
  restaurantId, trigger ("surprise"|"customer"|"practice"), orderId (opt), requestedBy (customerId|inspector|system),
  status (see §6.1), createdAt, startDeadlineAt, startedAt, finishDeadlineAt, completedAt,
  plannedChecks [checkId]  (server-only field; never sent to client before reveal),
  revealedChecks [{checkId, prompt, revealedAtServer, offsetSec}],
  liveness {prompt, revealedAtServer, offsetSec}   // expected answer stored in auditSecrets/{auditId}
  gps {lat,lng,accuracy}, distanceFromRegisteredM,
  videoPath, videoMime, durationSec,
  score, coverage, counted (bool), integrity {verdict, flags:[{code, detail, confidence}]},
  observedItems [{label, batchOrExpiry, state}], evidenceClips [{checkId, startSec, endSec}],
  coach {en:[string], hi:[string], or:[string]},
  modelId, promptVersion, usedCachedResult (bool)

audits/{auditId}/findings/{findingId}
  checkId, status ("pass"|"fail"|"not_verified"), severity, reason, timestamp ("MM:SS"),
  confidence, publicEligible (bool), needsReview (bool), disputed (bool),
  dispute {reason, at}, review {decision ("upheld"|"overturned"), by, at}

auditSecrets/{auditId}          // backend-only (rules deny clients)
  livenessExpected {n, object}

reviewQueue/{itemId}
  type ("dispute"|"integrity"), auditId, findingId (opt), restaurantId, createdAt, status ("open"|"resolved")

spotCheckLimits/{customerId_restaurantId}
  lastRequestAt
```

**Security rules (prototype level):** clients can **read** `restaurants`, `orders` (own), `audits` (non-secret fields), `findings`; **all writes go through the backend** (Admin SDK) except creating the Storage upload. `auditSecrets` deny all clients. Storage: authenticated users may write only `audits/{auditId}/recording.*`, content type `video/*`, max 150 MB.

---

## 11. API (FastAPI on Cloud Run, all under `/api`)

| Method & path | Body | Does |
|---|---|---|
| `POST /audits` | `{restaurantId, trigger, orderId?}` | Planner creates audit (random checks, liveness, deadlines). For `customer`: verify active order + limits. Returns `{auditId, startDeadlineAt}` |
| `POST /audits/{id}/start` | `{gps}` | Validates start window; sets `in_progress`, `finishDeadlineAt`; returns first instruction |
| `POST /audits/{id}/advance` | `{offsetSec}` | Logs reveal time/offset of current item; returns next instruction (check or liveness) or `{done:true}` |
| `POST /audits/{id}/complete` | `{videoPath, videoMime, durationSec}` | Sets `uploaded`, runs orchestrator synchronously (Cloud Run timeout 300 s), writes results; returns summary |
| `POST /audits/{id}/demo-sample` | `{sample: "messy"|"clean"|"too_perfect"}` | Demo only: attaches sample video + its prompt timeline, runs orchestrator (cached fallback) |
| `POST /findings/{auditId}/{findingId}/dispute` | `{reason}` | Marks disputed, hides from public score, adds to review queue, recomputes score |
| `POST /review/{itemId}` | `{decision}` | Inspector resolves; updates finding/integrity, recomputes score, tier, risk |
| `POST /inspector/surprise` | `{restaurantId?}` | Creates a surprise audit (random restaurant if none given) |
| `POST /scheduler/surprise` | header `X-Scheduler-Secret` | SHOULD: random surprise audits at peak hours |
| `POST /maintenance/expire` | — | Marks overdue audits `expired` (called by frontend poll in demo / scheduler in prod); updates missed checks |
| `GET /risk/ranking` | — | Returns ranked restaurants with reasons |
| `POST /demo/reset` | header secret | Re-seeds demo data |
| `GET /health` | — | `{ok:true, model}` |

Validation with Pydantic models. All timestamps server-side (UTC; display IST).

---

## 12. Gemini prompts and schemas

Store prompts in `backend/app/prompts/` with a `PROMPT_VERSION` constant. Use `temperature=0.2`.

### 12.1 Auditor prompt

```
You are a food-safety auditor reviewing a restaurant kitchen video recorded live on a phone.
The owner was shown instructions one at a time. The INSTRUCTION TIMELINE below says which
check the owner was asked to show and when (seconds from video start). Use it to find the
right part of the video for each check, but judge only what is actually visible or audible.

Rules:
- Judge ONLY what you can see. If a check was not shown clearly enough, status = "not_verified".
  Never guess "pass".
- Give the MM:SS timestamp of the clearest moment of evidence for every check.
- Confidence is 0 to 1. Be conservative.
- Never identify or describe people's faces or identities. For handler hygiene, judge only
  head covering, gloves/hands and apron.
- Also list any packaged items whose labels, batch numbers or expiry dates you can read
  (observedItems), and whether each looks unopened/full.
- Also verify the LIVENESS CHALLENGE: did the person do exactly the requested gesture near the
  requested object, around the stated time? Report what you saw.

CHECKS TO JUDGE (id: what to verify):
{checks_block}

INSTRUCTION TIMELINE:
{timeline_block}

LIVENESS CHALLENGE (shown at ~{liveness_offset}s): "{liveness_prompt}"

Return only JSON matching the schema.
```

**Auditor response schema**
```json
{
  "findings": [
    {"checkId": "string", "status": "pass|fail|not_verified", "reason": "string (one sentence)",
     "timestamp": "MM:SS", "confidence": 0.0}
  ],
  "liveness": {"observed": "string", "fingersCounted": 0, "nearObject": "string", "timestamp": "MM:SS", "confidence": 0.0},
  "observedItems": [{"label": "string", "batchOrExpiry": "string", "state": "unopened|opened|unclear"}],
  "evidenceClips": [{"checkId": "string", "startSec": 0, "endSec": 0}]
}
```

### 12.2 Integrity prompt

```
You are checking whether a kitchen audit video is genuine and live, not staged or edited.

Context:
- Orders received by this restaurant in the last hour: {orders_last_hour}
- Audit trigger: {trigger} (surprise/customer audits are unannounced)
- Reference description of this kitchen from its first verified audit: {reference_summary}

Look for:
1. Cuts, jumps, frozen frames, sudden changes in lighting or room (possible editing/splicing).
2. Whether this looks like the same kitchen as the reference (layout, tiles, equipment).
3. Activity level: does the kitchen look like it is actually operating (food being prepared,
   used utensils, waste in bins, open ingredient packs)? A spotless, empty, inactive kitchen
   during a busy hour is suspicious.
4. Signs that items were placed only for the camera (e.g. brand-new unopened packs everywhere,
   untouched surfaces next to a busy order count).

Judge only what you see. Do not identify people. Return only JSON matching the schema.
```

**Integrity response schema**
```json
{
  "continuousTake": {"ok": true, "detail": "string", "confidence": 0.0},
  "sameKitchenAsReference": {"ok": true, "detail": "string", "confidence": 0.0},
  "activityMatchesOrders": {"ok": true, "detail": "string", "confidence": 0.0},
  "propsSuspected": {"suspected": false, "detail": "string", "confidence": 0.0},
  "kitchenSummary": "string (2 sentences describing layout and equipment, used as future reference)"
}
```

**Integrity verdict (backend rules):**
- `failed` if liveness wrong/absent with confidence ≥ 0.7, OR distance from registered address > 200 m, OR `continuousTake.ok=false` with confidence ≥ 0.8.
- `suspicious` if any of: `sameKitchenAsReference.ok=false` (≥0.6), `activityMatchesOrders.ok=false` (≥0.6) while `ordersLastHour ≥ 10`, `propsSuspected` (≥0.6), repeated-props rule (§5.1 #10), finished in < 30% of expected time.
- else `clean`. On first verified clean audit, store `kitchenSummary` as the reference.

### 12.3 Coach prompt (text only)
Input: failed and not_verified findings. Output JSON `{ "en": [..], "hi": [..], "or": [..] }` — max 5 short, practical, respectful fix steps per language. Never shame; never mention penalties or law.

---

## 13. Build plan (phased; deploy after Phase 4)

**Phase 0 — Go/no-go (≤ 45 min)**
- Repo scaffold: `/frontend`, `/backend`, `/scripts`, `/demo-assets`, `firebase.json`, `README.md`.
- `scripts/test_auditor.py`: takes a local video path + a hard-coded timeline, calls Gemini with the Auditor prompt and schema, prints JSON. Run on the team's messy and clean test videos. **Pass:** detects raw meat above cooked food (or equivalent staged issue) and an open dustbin in the messy video; mostly passes the clean one; respects `not_verified`.

**Phase 1 — Backend core**
- FastAPI app, Firestore client, checks pool, planner, `/audits`, `/start`, `/advance`, `/complete`, auditor + integrity + scorer, `/health`. Seed script with 15 restaurants and orders.

**Phase 2 — Owner flow (frontend)**
- Vite React app, Firebase init, anonymous auth, owner dashboard with realtime request banner + countdown, Live Audit (camera, sequential reveals, liveness card, continuous recording, Storage upload), Report screen with evidence player.

**Phase 3 — Customer + Inspector**
- FoodieGo list, restaurant page, badge with tier/missed checks/disclaimer, order page with spot-check request and result. Inspector ranking, restaurant detail, review queue, trigger surprise audit.

**Phase 4 — Demo Mode + deploy**
- Sample videos, demo-sample endpoint, cached results, DEMO ribbon, `/tour`. **Deploy** Cloud Run + Firebase Hosting (§14). Smoke-test the public link on a laptop and a phone.

**Phase 5 — SHOULD features**
- Coach + language toggle, speech prompts, map, scheduler, dispute polish.

**Phase 6 — README + polish**
- README (§15), architecture diagram image, screenshots, final redeploy.

**Cut order if late:** Phase 5 items (bottom-up), then the map, then the guided tour (keep Demo Mode). **Never cut:** sequential random checks, liveness, Gemini scoring with timestamps, integrity check, badge with tier, customer spot check, inspector ranking, deployed link.

---

## 14. Deployment (Google Cloud — follow exactly)

### 14.1 One-time setup
```bash
# Project + region
gcloud config set project $PROJECT_ID
REGION=asia-south1

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com aiplatform.googleapis.com storage.googleapis.com \
  secretmanager.googleapis.com cloudscheduler.googleapis.com

# Firebase: add Firebase to the same GCP project (console or `firebase projects:addfirebase $PROJECT_ID`)
# Enable: Authentication → Anonymous; Firestore (Native, asia-south1); Storage (default bucket)

# Service account for Cloud Run
gcloud iam service-accounts create kitchenproof-api
SA=kitchenproof-api@$PROJECT_ID.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/aiplatform.user
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/datastore.user
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/storage.objectViewer
```
Vertex AI must be able to read the Storage bucket: the Cloud Run service account and the Vertex AI service agent in the same project need object read access (grant `roles/storage.objectViewer` on the bucket to the Vertex AI service agent if a permission error appears).

### 14.2 Backend (Cloud Run)
```bash
cd backend
gcloud run deploy kitchenproof-api --source . --region $REGION \
  --service-account $SA --allow-unauthenticated --timeout 300 --memory 1Gi \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=<model-id>,DEMO_MODE=true,STORAGE_BUCKET=<bucket> \
  --set-secrets SCHEDULER_SECRET=scheduler-secret:latest,ADMIN_SECRET=admin-secret:latest
```
Include a `Dockerfile` (python:3.12-slim, uvicorn on `$PORT`) or rely on buildpacks with `Procfile`.

### 14.3 Frontend (Firebase Hosting)
`firebase.json`:
```json
{
  "hosting": {
    "public": "frontend/dist",
    "ignore": ["firebase.json", "**/.*"],
    "rewrites": [
      { "source": "/api/**", "run": { "serviceId": "kitchenproof-api", "region": "asia-south1" } },
      { "source": "**", "destination": "/index.html" }
    ]
  },
  "firestore": { "rules": "firestore.rules", "indexes": "firestore.indexes.json" },
  "storage": { "rules": "storage.rules" }
}
```
```bash
cd frontend && npm ci && npm run build && cd ..
firebase deploy --only hosting,firestore:rules,firestore:indexes,storage
```
Frontend env (`frontend/.env.production`): Firebase web config values (public by design). API base is relative (`/api`) thanks to the rewrite — no CORS needed.

### 14.4 Optional scheduler
```bash
gcloud scheduler jobs create http surprise-audits --location $REGION \
  --schedule "*/30 12-15,19-23 * * *" --time-zone "Asia/Kolkata" \
  --uri https://<hosting-domain>/api/scheduler/surprise --http-method POST \
  --headers X-Scheduler-Secret=<secret>
```

### 14.5 Smoke test (must pass before submitting)
- Public link opens on a laptop (Chrome) and on a phone (Android Chrome + iPhone Safari).
- Demo tour runs end to end, including a **real** Gemini analysis on a sample video.
- Camera Live Audit works on a phone over HTTPS; upload succeeds; report appears.
- `/api/health` returns the model ID.

---

## 15. Submission checklist (owner: team)

- [ ] **Deployed link:** Firebase Hosting URL (and custom path `/tour` for judges).
- [ ] **Public GitHub repo** containing all code, `firebase.json`, rules, Dockerfile, seed script, and README.
- [ ] **README** sections: Problem · Solution · Demo link + how to try it in 2 minutes · Features · Anti-fake & anti-false design · Architecture diagram · Google tech used (Gemini model ID via Vertex AI, Cloud Run, Firebase Hosting, Firestore, Cloud Storage, Firebase Auth, Cloud Scheduler if used, ADK if used) · Local setup · Deploy steps · Limitations & roadmap · Disclaimer (not an FSSAI rating; demo data is fictional).
- [ ] **Demo video (< 3 min, public YouTube/Vimeo/Drive), English:**
  - 0:00–0:20 Problem: Mundhe raid headlines; "there will never be enough inspectors".
  - 0:20–0:35 FoodieGo: customer can't see the kitchen.
  - 0:35–1:20 Inspector triggers a surprise audit → owner countdown → live audit in a messy kitchen with random checks + liveness → score ~48 with timestamped evidence.
  - 1:20–1:45 Kitchen cleaned → customer requests a check during their order → passes ~87 → badge turns Silver.
  - 1:45–2:15 Anti-fake: "too-perfect" kitchen during a busy hour flagged; liveness explained; tiers explained.
  - 2:15–2:35 Fairness: dispute → inspector review; "not verified ≠ fail".
  - 2:35–3:00 Architecture (Gemini on Vertex AI, Cloud Run, Firebase) + scale (school mid-day meal kitchens, hostel messes, any country's food regulator).
- [ ] **Deck as PDF:** problem, why now, solution, demo screenshots, anti-fake layers, fairness safeguards, architecture, Google tech, impact & scale, roadmap (rider checks, FoodieGo/FSSAI integrations, Gemini Live voice guide), team.
- [ ] Theme selected: **Retail & Commerce**.
- [ ] Submitted on the Hack2skill dashboard **by midday 18 Oct IST**.

---

## 16. Repo layout

```
kitchenproof/
├─ CLAUDE.md                (this file)
├─ README.md
├─ firebase.json  firestore.rules  firestore.indexes.json  storage.rules  .firebaserc
├─ frontend/
│  ├─ index.html  vite.config.ts  tailwind.config.js  package.json
│  └─ src/
│     ├─ main.tsx  App.tsx  firebase.ts  api.ts  routes.tsx
│     ├─ pages/ (Landing, Tour, owner/*, customer/*, inspector/*)
│     ├─ components/ (ScoreBadge, TierIcon, IntegrityChip, FindingRow, EvidencePlayer, Countdown, StatusTimeline, CameraRecorder)
│     └─ lib/ (checks.ts, recorder.ts, time.ts)
├─ backend/
│  ├─ Dockerfile  requirements.txt
│  └─ app/
│     ├─ main.py  models.py  firestore.py  gemini.py  config.py
│     ├─ checks.py  liveness.py
│     ├─ agents/ (planner.py, auditor.py, integrity.py, coach.py, scorer.py, risk.py, orchestrator.py)
│     ├─ prompts/ (auditor.txt, integrity.txt, coach.txt, version.py)
│     └─ demo/ (seed.py, cached_results/*.json)
├─ scripts/ (test_auditor.py, seed_firestore.py, upload_demo_assets.py)
└─ demo-assets/ (messy_kitchen.mp4, clean_kitchen.mp4, too_perfect_kitchen.mp4 + timelines .json)
```

---

## 17. Things the team must do by hand (not code)

1. Record 3 sample videos (2–3 min each, phone, 720p) following a fixed timeline, and write each timeline JSON (check IDs + start seconds + liveness moment): **messy** (raw chicken packet on the top shelf above cooked food, open dustbin, a dirty counter), **clean** (same kitchen fixed), **too-perfect** (spotless, nothing cooking — used with a high order count).
2. Create the GCP project, enable billing, add Firebase, pick the Gemini model ID available in Vertex AI.
3. Film the final demo video and make the PDF deck.
4. Submit on Hack2skill.

---

## 18. Facts used in the pitch (cite in deck/README)

- Mundhe's Maharashtra FDA: 3,000+ raids since May 2026; permits suspended at Domino's, Pizza Hut and McDonald's outlets; viral photos of cockroaches, rats, rotting food — Reuters, 24 Aug 2026.
- Experts: inspections alone can't fix it; a consultant said the state ideally needs 2,000 food safety officers — AFP.
- FSSAI tightening rules for quick-delivery platforms and dark kitchens — 12 Oct 2026.
- Razorpay Fix My Itch Top 10: "Why can't consumers see verified kitchen safety standards on food delivery apps?"
- Prior art and gap: FSSAI Hygiene Rating (voluntary, third-party, rare), Zomato hygiene ratings (physical audits), China's kitchen livestreams (nobody watches; privacy backlash), CCTV AI for chains (private, needs installed cameras). KitchenProof: phone-only, unannounced, AI-verified, public.
