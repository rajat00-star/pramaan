# PraMaan

**Software System to Check Compliance of Packaged Commodities under the Legal
Metrology (Packaged Commodities) Rules, 2011** — SIH26034, Team U.L.T.R.O.N.

PraMaan turns a photograph of a product label into a legally-traceable
compliance verdict:

```
Product photo → preprocessing → label region → multilingual OCR → field extraction
             → deterministic rule engine (versioned rule pack) → verdict
             → evidence + legal clause → confidence gate → human review → audit trail
```

**The central design principle:** AI/CV does observation ("what text appears to
be on this label?"); it never decides law. A separate, deterministic,
versioned rule engine reads only from `docs/legal/rule_pack_v1.json` and
decides COMPLIANT / NON_COMPLIANT / REVIEW. No LLM is anywhere in that decision
path — `grep -rn "openai\|anthropic\|llm" backend/app` returns nothing.

This README covers what PraMaan does, how it's built, and exactly what is real
versus an honest placeholder. Deeper detail lives in:

- [`docs/architecture.md`](docs/architecture.md) — full system architecture
- [`docs/legal/rule_engine.md`](docs/legal/rule_engine.md) — rule versioning, provenance, reproducibility
- [`docs/security.md`](docs/security.md) — threat model and what's actually mitigated
- [`docs/deployment.md`](docs/deployment.md) — Docker, Postgres, environment config
- [`docs/mobile.md`](docs/mobile.md) — the React Native/Expo mobile app (citizen + inspector)
- [`docs/demo.md`](docs/demo.md) — the exact SIH demo script
- [`docs/legal/lmpc_2011_source.md`](docs/legal/lmpc_2011_source.md) — verbatim legal source citations

## 1. What PraMaan solves

Manual Legal Metrology inspection is slow, one-product-at-a-time, and
reactive — a citizen has no way to check a label before buying, and
enforcement can only spot-check a tiny fraction of packages in the market.
PraMaan makes that check instant, evidence-backed, and scalable: any citizen
or inspector can photograph a label and get a verdict citing the exact clause,
in seconds, with the underlying evidence (OCR text, bounding box, confidence)
attached — not "this looks non-compliant," but "Rule 6(1)(e) requires X, the
label declares Y, here is the crop that proves it."

**Explicitly out of MVP scope:** physical measurement of printed font size in
millimetres (Rule 8's requirement) — this needs a calibrated reference object
or known-DPI capture, which a phone photo alone can't reliably provide. This
is the deck's own stated MVP boundary, not a gap discovered later.

## 2. Problem statement

SIH26034, Theme: Agriculture, FoodTech & Rural Development. Full framing in
the original pitch deck; the engineering scope actually built covers 7 of the
mandatory declarations in Rule 6 of the Legal Metrology (Packaged
Commodities) Rules, 2011 (see `rule_pack_v1.json`): manufacturer/packer/
importer, country of origin (imported products only), common/generic name,
net quantity, date of manufacture, retail sale price, and consumer-care
details.

## 3. Architecture

Full detail in [`docs/architecture.md`](docs/architecture.md). Summary:

| Layer | What runs today |
|---|---|
| Web frontend | One static HTML/JS page ([`frontend/index.html`](frontend/index.html)) — login, citizen scan flow, inspector review, and a full **Department Dashboard** (overview KPIs, verdict-distribution chart, clickable case details with image/evidence/audit/replay, inspector activity, rule-pack info). Served by the same FastAPI process. |
| Mobile app | React Native + Expo + TypeScript, one app for both Citizen and Inspector roles ([`frontend/mobile/`](frontend/mobile/), see [`docs/mobile.md`](docs/mobile.md)). Same backend, same JWT auth, no legal logic duplicated on-device. |
| API | FastAPI, JWT auth, role-based authorization on every protected route |
| Pipeline | Preprocessing (OpenCV) → label detection (honest full-image fallback) → OCR (real Tesseract) → extraction (regex, English + Hindi keywords) → rule engine → verdict |
| Data | SQLAlchemy ORM; SQLite for local dev, PostgreSQL verified for production (see §11) |
| Storage | `ObjectStorage` abstraction — local filesystem implementation runs today; S3 interface defined, not implemented (no bucket in this environment) |

Synchronous by design for this scale: a scan runs inline in the request. The
deck's Redis-queue/worker architecture is addressed honestly, not built — see
§18 in `docs/architecture.md` for exactly what would change and why it isn't
needed yet at demo scale.

## 4. End-to-end pipeline

1. **Preprocessing** — grayscale, denoise, CLAHE contrast (real OpenCV, not a stub).
2. **Label detection** — `FullImageDetector` treats the whole photo as the label. No YOLOv8 weights or annotated dataset exist to train a real detector honestly; the `LabelDetector` interface and a `YOLOv8LabelDetector` stub already exist in [`app/pipeline/detection.py`](backend/app/pipeline/detection.py) so a trained model drops in without touching anything downstream.
3. **OCR** — real Tesseract 5.5.3, English + 8 Indic scripts installed. Real per-word confidence, never invented.
4. **Field extraction** — deterministic keyword/regex parser, English + Hindi keyword anchors (see §6).
5. **Rule engine** — the one place that decides compliance; see §5.
6. **Verdict + evidence** — every FAIL/REVIEW cites the source clause, the OCR'd text, and a bounding box.
7. **Confidence gate → human review** — see §7.
8. **Audit trail** — every lifecycle event logged immutably; see §8.

## 5. Legal rule architecture

The rule engine (`backend/app/pipeline/rule_engine.py`) is the only code
allowed to output COMPLIANT/NON_COMPLIANT/REVIEW. Full detail, including the
exact schema and every verified legal citation, is in
[`docs/legal/rule_engine.md`](docs/legal/rule_engine.md). Highlights:

- Every legal number (tolerance percentages, band thresholds) is **data** in `rule_pack_v1.json`, not a Python constant. `_validate_rule_pack()` fails the application at **startup** if a required legal parameter is missing or malformed — verified directly: pointed a broken rule pack at a real `uvicorn` process and watched it refuse to start.
- Every clause cited in a verdict (`"as required by Rule 6(1)(e)"`) is interpolated from the loaded rule pack's `clause` field, not a hardcoded string.
- Every scan stores `rule_pack_version` + a SHA-256 `rule_pack_hash` of the exact file bytes used.
- `GET /api/scans/{id}/replay` (inspector/admin) re-evaluates a scan's original extracted fields against the **exact historical rule-pack file**, located by content hash — proving reproducibility live, not just asserting it. A full v1→v2 introduction test (`tests/test_rule_pack_reproducibility.py`) proves a historical scan's verdict survives a newer version becoming active, using a throwaway temp rule pack, never the real legal file.

## 6. AI/OCR architecture — what's real vs abstraction

| Component | Status | Detail |
|---|---|---|
| OCR (Tesseract) | **REAL** | Not PaddleOCR — see rationale below. Real per-word confidence. |
| Multilingual OCR engine | **REAL** | Tesseract has English + Hindi/Bengali/Gujarati/Kannada/Marathi/Punjabi/Tamil/Telugu language data installed and genuinely tested (see `tests/test_multilingual_extraction.py`, which renders a real Devanagari label and OCRs it). |
| Multilingual field extraction | **PARTIAL** | Only Hindi keyword anchors added (7 field-anchor phrases). Verified directly: Devanagari *keywords* recognize reliably; Latin *digits* mixed into the same image (a price, a phone number) are measurably less reliable — this is stated, not hidden, in `extraction.py`'s module docstring. The other 7 installed languages have zero keyword coverage. |
| Label/region detection (YOLOv8) | **ABSTRACTION, not implemented** | No trained weights, no annotated dataset exist. `FullImageDetector` is the honest fallback running today; the `LabelDetector` interface is real and ready for a trained model. |
| Field extraction (LayoutLM-style) | **ABSTRACTION** | Current extraction is regex, not a layout model. Brittle on packaging with no keyword prefix (e.g. a bare product name) — documented in code, not silently accepted. |
| Legal decision-making | **Deterministic, not AI** | By design — see §5. |

### Why Tesseract instead of PaddleOCR
PaddleOCR needs the paddlepaddle framework plus multi-hundred-MB model
downloads, unverified in this environment. Tesseract is a real,
independently-verifiable engine that natively reports per-word confidence.
`OCREngine` is an explicit interface (`app/pipeline/ocr.py`) — adding
PaddleOCR later is one new class, not a rewrite.

## 7. Human review

Confidence-gated: a field below `CONFIDENCE_THRESHOLD` (default 60%) or not
found at all becomes `REVIEW`, never a silently-invented PASS/FAIL. Only
`inspector`/`department_admin` accounts can submit a correction
(`POST /api/scans/{id}/review`) — a `citizen` gets `403`.

Every correction is stored as an immutable `ReviewCorrection` row preserving
**before** (original OCR/extraction value), **after** (corrected value),
**who** (the authenticated reviewer's username — never client-supplied free
text; that was the original XSS vector, now closed at the source), **when**,
and the **verdict transition** (`previous_verdict` → `resulting_verdict`).
The original extracted value is never overwritten in the audit row even
though the live field is updated for future evaluation.

## 8. Evidence and audit model

Every rule evaluation carries `status`, `reason` (a full sentence, never
"Product is non-compliant"), `legal_reference`, `clause`, and `evidence`
(the OCR'd text, its bounding box when available, and for `net_quantity` the
full tolerance-band computation). `GET /api/scans/{id}/audit`
(inspector/admin only) exposes the full lifecycle: `SCAN_CREATED` →
`RULES_EVALUATED` → `SCAN_COMPLETED` (or `SCAN_FAILED`) → `FIELD_CORRECTED` →
`VERDICT_CHANGED`, each with actor and payload. Audit rows are append-only —
no route updates or deletes an `AuditLog` row.

## 9. Security

Full threat-model writeup in [`docs/security.md`](docs/security.md).
Summary of what's actually implemented and tested, not just intended:

- **Upload size**: a hard cap on the raw byte stream itself (not just Content-Length, not Starlette's `max_part_size` — verified directly that parameter doesn't limit file parts at all). See `tests/test_upload_limits.py`.
- **Pipeline failures**: every failure (expected or a raw `DecompressionBombError`/`RuntimeError`) results in a safe generic client message, a full server-side logged traceback, and `Scan.status = "ERROR"` — never a stuck `PROCESSING` row or a leaked file path. See `tests/test_pipeline_error_handling.py`.
- **XSS**: every user-influenced value rendered in the frontend goes through `escapeHtml()` — including the one field (`reviewer`) that used to be free client text and wasn't escaped; it's no longer client-settable at all (identity comes from the authenticated session server-side).
- **Authentication**: JWT (HS256), bcrypt password hashing (not passlib — see `app/auth.py`'s docstring for why), demo accounts seeded from environment config, never hardcoded.
- **Authorization / IDOR**: a `citizen` sees only their own scans (`GET /api/scans/{id}` on someone else's scan → `404`, not `403`, so existence isn't confirmed either); `inspector`/`department_admin` can see all scans; review/audit/dashboard/replay are role-gated server-side, not hidden by the frontend.
- **Object access**: images are served only via an authenticated, ownership-checked `GET /api/scans/{id}/image` — there is no public static file mount.
- **CORS**: defaults to local-dev origins only, never `"*"` (a real bug — pydantic-settings JSON-decoding a comma-separated env value — was caught and fixed while wiring this up; see `tests/test_config.py`).

## 10. API

All routes except `/api/auth/login`, `/api/health`, `/api/readiness` require
`Authorization: Bearer <token>`.

| Method & path | Auth | Purpose |
|---|---|---|
| `POST /api/auth/login` | — | `username`+`password` (form-encoded) → JWT |
| `GET /api/auth/me` | any | Current user's identity |
| `POST /api/scans` | any | Upload an image, run the pipeline synchronously, return the scan |
| `GET /api/scans` | any | List scans (citizen: own only; inspector/admin: all); `status_filter`/`verdict_filter` |
| `GET /api/scans/{id}` | any (ownership-checked) | Full scan detail |
| `GET /api/scans/{id}/image` | any (ownership-checked) | The original uploaded image |
| `POST /api/scans/{id}/review` | inspector/admin | Submit a field correction |
| `GET /api/scans/{id}/audit` | inspector/admin | Full audit trail for one scan |
| `GET /api/scans/{id}/replay` | inspector/admin | Re-evaluate against the scan's original rule-pack file; proves reproducibility |
| `GET /api/dashboard/summary` | inspector/admin | Aggregate counts, violation frequency, recent scans |
| `GET /api/rules` | any | Current rule pack (version, hash, fields) |
| `GET /api/health` | — | Liveness |
| `GET /api/readiness` | — | Dependency checks: database, rule pack, OCR engine |

Interactive OpenAPI docs at `/docs` once running.

### Sample requests

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=citizen_demo&password=citizen123" | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/scans \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/label.jpg;type=image/jpeg"

curl http://localhost:8000/api/scans/<scan_id> -H "Authorization: Bearer $TOKEN"
```

## 11. Database

SQLAlchemy models: `User`, `Scan`, `ExtractedField`, `RuleEvaluation`,
`ReviewCorrection`, `AuditLog` — see `backend/app/models.py`. Indexes on
`Scan.status`, `Scan.overall_verdict`, `Scan.created_at`, `Scan.owner_user_id`,
`Scan.rule_pack_version/hash`, `User.username/role`, and composite
`(scan_id, created_at)` indexes on `AuditLog`/`ReviewCorrection` for the
query patterns the dashboard and audit views actually use.

**PostgreSQL compatibility is verified, not just claimed**: during
development, a real local PostgreSQL 16 instance had the full schema created
against it via `init_db()`, then a complete authenticated scan cycle (login →
upload → verdict → dashboard aggregation) was run against it end-to-end
through the actual running server. SQLite remains the default for zero-setup
local dev. No formal migration tool (Alembic) is included — `create_all()` is
sufficient for a schema with no migration history yet; this is a genuine gap
for a long-lived production deployment, disclosed in §12 of
`docs/architecture.md`, not silently worked around.

## 12. Deployment

Full instructions in [`docs/deployment.md`](docs/deployment.md). `docker
compose up -d --build` has been run and verified directly: both containers
(`app`, `db`) come up healthy, PostgreSQL 16 is the real datastore (not
SQLite), login/scan/dashboard all work end-to-end against it at
`http://127.0.0.1:8000`, and `/docs` (Swagger) serves correctly. Native
(non-Docker) setup below also still works and is the faster loop for local
development.

## 13. Testing

```bash
cd backend
source .venv/bin/activate
pytest -q                                   # all tests
pytest -q -s tests/test_pipeline_e2e.py     # real photo -> OCR -> verdict, with printed output
ruff check app tests                        # lint (also runs in CI)
```

**117 tests, 117 passing, 1 intentionally skipped** (confirmed by actually running the suite — see the
CHANGES/verification trail in project history for the exact numbers at each
stage of development, not asserted here without having run it). Categories:
rule-engine unit tests (First Schedule Table I/II boundaries, confidence
gating, verdict aggregation), extraction unit tests, rule-pack integrity
tests (data-driven legal parameters, loud failure on a broken pack), a full
v1→v2 rule-pack reproducibility + replay test against the real API, upload
size boundary tests, pipeline error-handling tests (including a genuine
`PIL.DecompressionBombError`), auth/RBAC/IDOR tests, dashboard tests, and
multilingual (Hindi) extraction tests using real Tesseract OCR on a
real-font-rendered image. Two E2E fixtures — one compliant, one deliberately
non-compliant (MRP missing the "inclusive of all taxes" wording required by
Rule 6(1)(e)) — are generated at test time and run through the real HTTP API
with real OCR, not mocked.

## 14. Limitations

Full, itemized list in each doc's own "remaining debt" section; the honest
summary:

- No queue/worker split — synchronous pipeline, fine at demo scale, not the deck's stated scaling architecture.
- No Alembic migrations.
- YOLOv8 detection and LayoutLM-style extraction are documented abstractions, not trained models.
- Multilingual field extraction covers Hindi keywords only, with a measured (not assumed) mixed-script digit-OCR weakness.
- `common_generic_name` extraction is the weakest of the seven fields (keyword-prefix dependent).
- Net-quantity checking validates the *declaration*, not the package's actual physical contents (no scale in the loop) — stated in every such evaluation's evidence.
- Font-size-in-mm measurement: explicitly out of MVP scope per the original deck.
- CI (GitHub Actions) is written but doesn't run locally — Docker itself is now verified (see §12), CI execution is not.
- OCR-level determinism is NOT guaranteed across different Tesseract builds (verified directly: the same real photo produced a clean COMPLIANT verdict on Docker's Tesseract 5.5.0 but REVIEW with corrupted evidence text on local Homebrew Tesseract 5.5.3 — see `docs/demo/golden_dataset/compliant_tata_tea_docker/evidence.md`). Legal-rule-level reproducibility (`/replay`, rule-pack-hash-based) is unaffected by this and holds perfectly.
- Mobile app camera/gallery capture could not be tested on a real device or simulator in this environment (no Xcode, no Android SDK) — verified instead via `expo start --web` against the live Docker backend and via TypeScript strict-mode compilation. See `docs/mobile.md` for exactly what was and wasn't verified.

## 15a. Mobile app

One React Native + Expo + TypeScript app for both **Citizen** and
**Inspector** roles (`frontend/mobile/`) — role-based routing after login,
server-side RBAC remains authoritative. Full setup, physical-device
networking, and exactly what was/wasn't verified: [`docs/mobile.md`](docs/mobile.md).

```bash
cd frontend/mobile
npm install
cp .env.example .env   # set EXPO_PUBLIC_API_URL for your target — see docs/mobile.md
npx expo start
```

Citizen: scan a label (camera or gallery) → real OCR/extraction/rule-engine
verdict → evidence → history. Inspector: review queue → case detail (real
image + evidence) → correct a field → audit-recorded. No legal rule, OCR, or
extraction logic runs on-device — the mobile app is a client of the same
backend and APIs as the website.

## 15. Demo instructions

See [`docs/demo.md`](docs/demo.md) for the exact 3–5 minute walkthrough
(citizen scan → REVIEW → inspector correction → audit trail → dashboard →
replay proving reproducibility).

## Setup (what was actually run to produce every result in this README)

```bash
# 1. OCR engine + Indic language packs (a system binary, not a Python package)
brew install tesseract tesseract-lang

# 2. Python environment
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure (optional — defaults work out of the box for local dev)
cp .env.example .env

# 4. Run
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000, sign in with a demo account (see
`.env.example`), and use the app.
