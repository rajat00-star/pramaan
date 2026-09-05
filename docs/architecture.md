# PraMaan Architecture

## 1. Design principle

AI/CV produces **observations**. A deterministic rule engine produces
**decisions**. A human resolves **uncertainty**. These three are architecturally
separate — no code path lets an OCR confidence score or an extraction guess
become a legal verdict without passing through `rule_engine.py`, and nothing
in that module calls an LLM or any statistical model.

```
Image → Preprocess → Detect region → OCR → Extract fields → Rule engine → Verdict
                                                                  │
                                                    confidence < threshold?
                                                                  │
                                                                  ▼
                                                            Human review
                                                                  │
                                                                  ▼
                                                        Re-evaluate → new verdict
                                                                  │
                                                                  ▼
                                                            Audit trail
```

## 2. Component map

| Module | Responsibility | Status |
|---|---|---|
| `app/pipeline/preprocessing.py` | Grayscale, denoise (`fastNlMeansDenoising`), CLAHE contrast | Real |
| `app/pipeline/detection.py` | `LabelDetector` interface; `FullImageDetector` (real fallback); `YOLOv8LabelDetector` (stub, documented) | Real interface, honest fallback |
| `app/pipeline/ocr.py` | `OCREngine` interface; `TesseractOCREngine` (real) | Real |
| `app/pipeline/extraction.py` | Keyword/regex field extraction, English + Hindi | Real, documented limitations |
| `app/pipeline/rule_engine.py` | The only place COMPLIANT/NON_COMPLIANT/REVIEW is decided | Real, the core of the project |
| `app/pipeline/pipeline.py` | Orchestrates the above; converts exceptions to safe `PipelineResult`s | Real |
| `app/auth.py` | JWT issuance/verification, bcrypt hashing, role dependency factories | Real |
| `app/storage.py` | `ObjectStorage` interface; `LocalObjectStorage` (real); `S3ObjectStorage` (documented, not implemented) | Real + honest abstraction |
| `app/routes/*.py` | FastAPI routers: scan, review, audit, dashboard, rules, auth | Real |
| `app/models.py` | SQLAlchemy ORM, Postgres-compatible types throughout | Real |

## 3. Data flow for one scan

1. `POST /api/scans` — authenticated. Upload is size-capped on the raw byte stream (see `docs/security.md`), stored via `ObjectStorage` under a server-generated key.
2. `run_pipeline()`: preprocess → detect (whole image today) → OCR (Tesseract, configured language(s)) → extract fields (regex) → load the active rule pack → evaluate every field → aggregate verdict.
3. Every stage's failure mode converts to a safe, logged `PipelineResult` — nothing propagates a raw exception to the client (see `app/routes/scan.py`'s `try/except Exception` boundary and `docs/security.md`).
4. Persist: `Scan`, `ExtractedField` rows, `RuleEvaluation` rows, `AuditLog` rows (`SCAN_CREATED`, `RULES_EVALUATED`, `SCAN_COMPLETED`/`SCAN_FAILED`).
5. If any field lands in `REVIEW`, an inspector/admin can `POST /api/scans/{id}/review`; this re-runs `evaluate_field()` for that one field against the **same rule-pack version**, recomputes the aggregate verdict, and logs `FIELD_CORRECTED` + (if the verdict changed) `VERDICT_CHANGED`.

## 4. Why synchronous, not queued

The deck describes a Redis-backed job queue with stateless OCR/CV workers.
That architecture matters at production scale (many concurrent scans,
independent worker autoscaling); at hackathon/demo scale, a single Tesseract
call takes well under a second and running it inline keeps the system easier
to reason about and to verify end-to-end. The honest statement of what would
change for production:

- `POST /api/scans` would enqueue a job and return `202` with a scan id immediately.
- A worker pool (Celery/RQ against Redis, or an async task queue) would run `run_pipeline()` out-of-process.
- The frontend would poll or use a websocket for the `PROCESSING → DONE/ERROR` transition it currently gets synchronously.

None of this is implemented. It's a deliberate scope decision for this stage,
not a discovered gap — flagged here so no one mistakes "works today" for
"scales as-is."

## 5. Storage

`app/storage.py` defines `ObjectStorage` with `save()`/`url_for()`.
`LocalObjectStorage` (filesystem) is what actually runs. `S3ObjectStorage` is
defined with the same interface and raises `NotImplementedError` — there is no
S3-compatible bucket or credentials in this environment to integrate against
honestly. Object keys are always server-generated (`<uuid4hex><allowed-ext>`),
never derived from a client-supplied filename, so swapping storage backends
changes nothing about path-traversal safety.

## 6. Database

See README §11 for the verified-Postgres claim. Schema: `User`, `Scan`
(owns `owner_user_id`, `rule_pack_version`, `rule_pack_hash`, indexed on
status/verdict/created_at/owner), `ExtractedField`, `RuleEvaluation`,
`ReviewCorrection` (before/after/who/when/verdict-transition), `AuditLog`
(append-only, indexed on `(scan_id, created_at)` and `event_type`).

## 7. What's real vs abstraction vs out of scope

| Component | Classification |
|---|---|
| OCR (Tesseract) | REAL |
| Legal rule engine | REAL |
| Rule versioning + reproducibility + replay | REAL |
| Human review workflow | REAL |
| Audit trail | REAL |
| Authentication / RBAC | REAL |
| PostgreSQL support | REAL (verified against a live instance) |
| Object storage (local) | REAL |
| Multilingual OCR engine | REAL |
| Multilingual field extraction | PARTIAL (Hindi keywords only) |
| Label detection (YOLOv8) | ABSTRACTION — interface real, model not trained |
| Layout-aware extraction | ABSTRACTION — not built, regex used instead |
| Object storage (S3) | ABSTRACTION — interface defined, not implemented |
| Queue/async architecture | OUT OF SCOPE for this stage — addressed honestly above, not built |
| Docker/CI | Written, not executed in this environment (no Docker installed here) |
| Department dashboard | REAL (real aggregate SQL queries, not mock data) |
| Font-size-in-mm measurement | OUT OF SCOPE — stated MVP boundary from the original deck |
