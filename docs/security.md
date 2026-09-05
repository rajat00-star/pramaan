# PraMaan Security

This documents what's actually implemented and tested, organized by threat.
Anything not covered here is a real gap — see "Not addressed" at the bottom,
not an implied claim of coverage.

## Upload handling

**Threat**: unbounded memory/disk consumption from a huge or malicious upload.

Two layers in `app/routes/scan.py`:
1. A fast Content-Length-based rejection (best-effort; a client can lie about or omit this header).
2. The authoritative check: `_size_capped_stream()` wraps the raw request body stream and raises the instant more than `max_upload_mb` has been seen, *before* that data reaches the multipart parser. This exists because two things that look like they'd solve this don't: FastAPI's automatic `file: UploadFile = File(...)` parameter, and even Starlette's own `MultiPartParser(max_part_size=...)` — verified directly against this installation that `max_part_size` only limits ordinary form *fields*, not file parts, so a multi-gigabyte file sails through it untouched regardless of the value passed.

Tested in `tests/test_upload_limits.py`: below/at/over the limit, with
Content-Length present and deliberately stripped, and that a rejected upload
never creates a `Scan` row (nothing left stuck in `PROCESSING`).

**Threat**: decompression bombs, malformed images, corrupted files.

`preprocessing.py` wraps `Image.open()`/`.verify()`/`.load()`; anything not
caught there (a `DecompressionBombError`, which Pillow raises directly as an
`Exception` subclass, not via the caught exception types) is caught by a
last-resort `try/except Exception` around the whole pipeline call in
`routes/scan.py`. Both paths result in `Scan.status = "ERROR"` with a fixed,
generic client-facing message — never the raw exception text, which for PIL
and Tesseract errors can include the server's temp file path (a real leak,
caught and fixed during development — see `preprocessing.py`'s comment).
Tested in `tests/test_pipeline_error_handling.py`, including a genuine
`monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)` to trigger a real
`DecompressionBombError`, not a simulated one.

## Injection

**SQL injection**: not applicable by construction — every query goes through
SQLAlchemy's ORM with parameter binding; `grep -rn "\.execute(f['\"]"` finds
nothing.

**XSS**: the frontend escapes every user-influenced value it renders via a
single `escapeHtml()` helper. One field was missed originally — `reviewer` in
the review-history table, which was also client-settable free text at the
time — a genuine stored-XSS-shaped bug caught during a security audit pass.
Fixed two ways: `escapeHtml()` now covers it, and (more fundamentally) it's no
longer client-settable at all — `schemas.ReviewCorrectionIn` has no
`reviewer` field; the reviewer's identity is always taken from the
authenticated session server-side (`current_user.username`).

**Path traversal**: object storage keys are always server-generated
(`<uuid4hex><allowed-extension>`), never derived from the client's filename.
`LocalObjectStorage.save()`'s docstring states this explicitly as the reason
it's safe.

**Log injection**: log calls use `%`-style lazy formatting
(`logger.info("scan %s completed: %s", scan.id, verdict)`), not f-string
interpolation of untrusted values into a format string.

## Authentication and authorization

- **Passwords**: bcrypt via the `bcrypt` package directly (not `passlib` —
  `passlib==1.7.4`'s bcrypt backend detection is broken against
  `bcrypt>=4.0` in this environment, verified directly by hitting the actual
  exception before switching approaches; documented in `app/auth.py`).
- **Tokens**: JWT (HS256), signed with `SECRET_KEY`. If unset, a random key
  is generated per process — fine for a demo (tokens just stop validating on
  restart), **wrong for production** (a multi-worker deployment would
  disagree with itself); `get_settings()` emits a `UserWarning` every time
  this happens, and `.env.example` says so directly.
- **Login errors**: an unknown username and a correct-username-wrong-password
  both return the identical error message and status code, preventing
  username enumeration — tested in `test_auth.py`.
- **Authorization (RBAC)**: enforced server-side via FastAPI dependencies
  (`auth.require_roles(...)`), not by the frontend hiding a button. Citizens
  cannot submit reviews (`403`), view the dashboard (`403`), or view another
  user's audit trail/scan (see IDOR below).
- **IDOR**: `GET /api/scans/{id}` and `GET /api/scans/{id}/image` check
  `scan.owner_user_id` against the authenticated citizen; a non-owner gets
  `404`, not `403` — deliberately, so a citizen probing scan IDs can't even
  learn that a given ID exists. Proven with a genuinely separate second
  citizen account in `test_pipeline_e2e.py::test_citizen_cannot_see_another_citizens_scan`,
  not the same account re-used.
- **Image serving**: there is no public static file mount for uploads (the
  earlier prototype had one) — every image fetch goes through the
  authenticated, ownership-checked `/api/scans/{id}/image` endpoint.

## CORS

Defaults to local-dev origins only (`http://localhost:8000`,
`http://127.0.0.1:8000`), configurable via `CORS_ALLOW_ORIGINS` — never `"*"`,
because authenticated requests carry a bearer token that a wildcard policy
would expose to any origin able to get a user's browser to call this API. A
real bug was caught and fixed while wiring this up: pydantic-settings tries
to JSON-decode env values for tuple/list-typed settings fields, which crashes
outright on a plain comma-separated string — `cors_allow_origins` is
deliberately typed `str` with a `.cors_allow_origins_list` property instead;
regression-tested in `tests/test_config.py`.

## Observability without leakage

Every request gets a correlation id (`X-Request-ID` header, generated if the
client didn't send one) attached to its log lines. Readiness
(`/api/readiness`) reports dependency health (database, rule pack, OCR
engine) without ever including exception text, stack traces, or connection
strings in the response body — only the exception's *class name*.

## Not addressed (real gaps, not implied coverage)

- **Rate limiting** — no throttling on login attempts or scan uploads. A real deployment needs this; not built here.
- **CSRF** — not applicable in the current design (bearer-token auth via `Authorization` header, no cookies), but this stops being true the moment a cookie-based session is introduced — worth re-checking then, not assumed safe forever.
- **Secrets management** — `.env` file / environment variables only; no integration with a secrets manager (Vault, AWS Secrets Manager, etc.).
- **Dependency vulnerability scanning** — not run in CI. `pip-audit`/`safety` would be the next addition.
- **TLS termination** — assumed to be handled by whatever sits in front of this process (a reverse proxy, a cloud load balancer) in any real deployment; the app itself speaks plain HTTP.
