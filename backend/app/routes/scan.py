import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile  # what our manual form parsing returns
from starlette.formparsers import MultiPartParser

from app import auth, models, schemas
from app.config import Settings, get_settings
from app.db import get_db
from app.models import ROLE_CITIZEN
from app.pipeline.pipeline import run_pipeline
from app.storage import get_object_storage

logger = logging.getLogger("pramaan.scan")
router = APIRouter(prefix="/api/scans", tags=["scans"])

EXTENSION_BY_CONTENT_TYPE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# Allowance for multipart boundary/header framing around the single "file" part
# (boundary markers + Content-Disposition/Content-Type header lines are typically
# well under 300 bytes; this leaves generous margin for a long filename) so a file
# of exactly max_upload_mb isn't rejected for a few hundred bytes of protocol
# overhead it never controlled.
_MULTIPART_OVERHEAD_BYTES = 2048


class _UploadTooLarge(Exception):
    pass


def _declared_content_length_exceeds(content_length_header: str | None, max_bytes: int) -> bool:
    """Best-effort check against the client-declared Content-Length.

    A client can omit this header or lie about it, so this is only ever a fast
    rejection path for the obvious cases — the authoritative limit is
    `_size_capped_stream` below, which counts actual bytes received.
    """
    if content_length_header is None:
        return False
    try:
        declared = int(content_length_header)
    except ValueError:
        return False
    return declared > max_bytes + _MULTIPART_OVERHEAD_BYTES


async def _size_capped_stream(stream: AsyncIterator[bytes], max_bytes: int) -> AsyncIterator[bytes]:
    """Re-yield a request body stream, aborting the instant more than `max_bytes`
    has been seen — before that excess data is ever handed to the multipart parser.

    This is the actual hard limit. Starlette's own `MultiPartParser` accepts a
    `max_part_size` argument, but it only enforces that cap on ordinary form
    FIELDS — verified directly against this installation: a file part is written
    to its spooled temp file with no size check at all regardless of that
    argument. So the only way to guarantee the server never buffers an
    arbitrarily large upload is to cap the raw byte stream ourselves, upstream
    of any multipart parsing.
    """
    total = 0
    async for chunk in stream:
        total += len(chunk)
        if total > max_bytes:
            raise _UploadTooLarge(max_bytes)
        yield chunk


@router.post(
    "",
    response_model=schemas.ScanOut,
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {"file": {"type": "string", "format": "binary"}},
                        "required": ["file"],
                    }
                }
            },
        }
    },
)
async def create_scan(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: models.User = Depends(auth.get_current_user),
) -> models.Scan:
    max_bytes = int(settings.max_upload_mb * 1024 * 1024)

    # Layer 1 (fast path): reject an obviously-oversized request before touching the
    # body at all. Best-effort only — see _declared_content_length_exceeds.
    if _declared_content_length_exceeds(request.headers.get("content-length"), max_bytes):
        raise HTTPException(status_code=413, detail=f"File exceeds max upload size of {settings.max_upload_mb} MB")

    # Layer 2 (authoritative): parse the body ourselves through a size-capped stream
    # instead of the automatic `file: UploadFile = File(...)` parameter, so the cap
    # is enforced on the raw bytes as they arrive, regardless of Content-Length.
    try:
        # The raw stream carries multipart boundary/header framing in addition to
        # the file's own bytes, so the cap here allows the same small overhead as
        # layer 1 — otherwise a file of exactly `max_bytes` would be rejected for
        # a few hundred bytes of protocol framing it never controlled.
        parser = MultiPartParser(
            request.headers, _size_capped_stream(request.stream(), max_bytes + _MULTIPART_OVERHEAD_BYTES)
        )
        form = await parser.parse()
    except _UploadTooLarge:
        raise HTTPException(status_code=413, detail=f"File exceeds max upload size of {settings.max_upload_mb} MB") from None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not parse the uploaded form data") from exc

    try:
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise HTTPException(status_code=422, detail="Expected an uploaded file in the 'file' field")

        if file.content_type not in settings.allowed_content_types:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported content type '{file.content_type}'. Allowed: {list(settings.allowed_content_types)}",
            )

        contents = await file.read()  # safe: already bounded by max_part_size above
        if len(contents) == 0:
            raise HTTPException(status_code=422, detail="Uploaded file is empty")

        filename = file.filename
        content_type = file.content_type
    finally:
        await form.close()

    ext = EXTENSION_BY_CONTENT_TYPE.get(content_type, Path(filename or "").suffix or ".bin")
    scan_id = uuid.uuid4().hex
    object_key = f"{scan_id}{ext}"  # server-generated — never derived from the client's filename
    storage = get_object_storage(settings.upload_dir)
    storage.save(object_key, contents)
    dest_path = settings.upload_dir / object_key  # local-storage-backed today; see app/storage.py

    scan = models.Scan(id=scan_id, owner_user_id=current_user.id, image_path=object_key, status="PROCESSING")
    db.add(scan)
    db.add(
        models.AuditLog(
            scan_id=scan.id, event_type="SCAN_CREATED", actor_user_id=current_user.id, payload={"filename": filename}
        )
    )
    db.commit()

    try:
        result = run_pipeline(dest_path, settings)
    except Exception:
        # Last-resort safety net: anything the pipeline didn't already convert into
        # a PramaanImageError/PramaanOCRError (a decompression bomb, an unexpected
        # library crash, etc.) lands here. The scan must never stay stuck in
        # PROCESSING, the client must never see internals, and the real exception
        # must still be diagnosable from the server logs.
        logger.exception("scan %s: unexpected exception while running the pipeline", scan.id)
        db.rollback()
        scan.status = "ERROR"
        scan.error_message = "An unexpected error occurred while analyzing this image. Please try again."
        db.add(
            models.AuditLog(
                scan_id=scan.id,
                event_type="SCAN_FAILED",
                actor_user_id=current_user.id,
                payload={"error": "unexpected_pipeline_exception"},
            )
        )
        db.commit()
        db.refresh(scan)
        return scan

    if result.status == "ERROR":
        scan.status = "ERROR"
        scan.error_message = result.error_message
        db.add(
            models.AuditLog(
                scan_id=scan.id,
                event_type="SCAN_FAILED",
                actor_user_id=current_user.id,
                payload={"error": result.error_message},
            )
        )
        db.commit()
        db.refresh(scan)
        logger.warning("scan %s failed: %s", scan.id, result.error_message)
        return scan

    scan.status = "DONE"
    scan.detector_method = result.detector_method
    scan.ocr_engine = result.ocr_result.engine if result.ocr_result else None
    scan.ocr_lang = result.ocr_result.lang if result.ocr_result else None
    scan.raw_ocr_text = result.ocr_result.full_text if result.ocr_result else None
    scan.ocr_mean_confidence = result.ocr_result.mean_confidence if result.ocr_result else None
    scan.rule_pack_version = result.rule_pack_version
    scan.rule_pack_hash = result.rule_pack_hash
    scan.overall_verdict = result.overall_verdict
    scan.overall_confidence = result.overall_confidence

    for field_id, extracted in result.extracted_fields.items():
        db.add(
            models.ExtractedField(
                scan_id=scan.id,
                field_id=field_id,
                found=extracted.found,
                raw_value=extracted.raw_value,
                confidence=extracted.confidence,
                bbox=extracted.bbox,
                source="ocr",
            )
        )

    for ev in result.rule_evaluations:
        db.add(
            models.RuleEvaluation(
                scan_id=scan.id,
                field_id=ev.field_id,
                clause=ev.clause,
                legal_reference=ev.legal_reference,
                status=ev.status,
                reason=ev.reason,
                evidence=ev.evidence,
                rule_pack_version=ev.rule_pack_version,
            )
        )

    db.add(
        models.AuditLog(
            scan_id=scan.id,
            event_type="RULES_EVALUATED",
            actor_user_id=current_user.id,
            payload={
                "rule_pack_version": scan.rule_pack_version,
                "rule_pack_hash": scan.rule_pack_hash,
                "statuses": {ev.field_id: ev.status for ev in result.rule_evaluations},
            },
        )
    )
    db.add(
        models.AuditLog(
            scan_id=scan.id,
            event_type="SCAN_COMPLETED",
            actor_user_id=current_user.id,
            payload={"overall_verdict": scan.overall_verdict},
        )
    )

    db.commit()
    db.refresh(scan)
    logger.info("scan %s completed: %s", scan.id, scan.overall_verdict)
    return scan


@router.get("", response_model=list[schemas.ScanSummaryOut])
def list_scans(
    limit: int = 20,
    status_filter: str | None = None,
    verdict_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> list[models.Scan]:
    query = db.query(models.Scan)
    # IDOR protection: a citizen sees only their own scans; inspectors/admins can
    # see everything (enforcement staff need cross-citizen visibility by design).
    if current_user.role == ROLE_CITIZEN:
        query = query.filter(models.Scan.owner_user_id == current_user.id)
    if status_filter:
        query = query.filter(models.Scan.status == status_filter)
    if verdict_filter:
        query = query.filter(models.Scan.overall_verdict == verdict_filter)
    return query.order_by(models.Scan.created_at.desc()).limit(min(limit, 200)).all()


def _get_scan_or_404_with_ownership_check(scan_id: str, db: Session, current_user: models.User) -> models.Scan:
    scan = db.get(models.Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if current_user.role == ROLE_CITIZEN and scan.owner_user_id != current_user.id:
        # 404, not 403 — do not confirm to an unauthorized caller that this scan
        # ID exists at all.
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}", response_model=schemas.ScanOut)
def get_scan(
    scan_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)
) -> models.Scan:
    return _get_scan_or_404_with_ownership_check(scan_id, db, current_user)


@router.get("/{scan_id}/image")
def get_scan_image(
    scan_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: models.User = Depends(auth.get_current_user),
) -> FileResponse:
    """Serves the original uploaded image — authenticated and ownership-checked,
    unlike a plain static file mount (which would let anyone who guesses or
    obtains a scan's object key view another citizen's uploaded photo)."""
    scan = _get_scan_or_404_with_ownership_check(scan_id, db, current_user)
    image_path = settings.upload_dir / scan.image_path
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)
