import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.auth import seed_demo_users
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.pipeline import rule_engine
from app.routes import audit, auth_routes, dashboard, review, rules, scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s [%(request_id)s]: %(message)s")


class _RequestIdDefaultFilter(logging.Filter):
    """So log lines from code paths without a request in scope (startup, background
    work) still have a %(request_id)s to format — avoids a KeyError from the
    formatter above rather than only working when RequestIdMiddleware set one."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logging.getLogger().addFilter(_RequestIdDefaultFilter())

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    # Fail loudly at startup, not on the first scan request, if the rule pack is
    # missing or has a malformed machine-readable legal parameter.
    rule_engine.load_rule_pack(str(settings.rule_pack_path))
    db = SessionLocal()
    try:
        seed_demo_users(db, settings)
    finally:
        db.close()
    yield


app = FastAPI(
    title="PraMaan",
    description="Photo-to-verdict Legal Metrology (Packaged Commodities) compliance checker.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins_list),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_timing(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logging.getLogger("pramaan.http").info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"request_id": request_id},
    )
    return response


app.include_router(auth_routes.router)
app.include_router(scan.router)
app.include_router(review.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(rules.router)


@app.get("/api/health")
def health() -> dict:
    """Liveness only: is the process up and responding at all."""
    return {"status": "ok"}


@app.get("/api/readiness")
def readiness() -> dict:
    """Are this process's actual dependencies usable: the database, the rule
    pack, and the OCR engine — not just "is the process running"."""
    checks: dict[str, str] = {}

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — readiness must report, never crash, on a dependency failure
        checks["database"] = f"error: {exc.__class__.__name__}"

    try:
        rule_engine.load_rule_pack(str(settings.rule_pack_path))
        checks["rule_pack"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["rule_pack"] = f"error: {exc.__class__.__name__}"

    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        checks["ocr_engine"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["ocr_engine"] = f"error: {exc.__class__.__name__}"

    ready = all(v == "ok" for v in checks.values())
    return {"ready": ready, "checks": checks}


_frontend_dir = settings.upload_dir.parent.parent / "frontend"  # BACKEND_DIR.parent == REPO_ROOT
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
