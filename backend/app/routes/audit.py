from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import Settings, get_settings
from app.db import get_db
from app.models import ROLE_DEPARTMENT_ADMIN, ROLE_INSPECTOR
from app.pipeline import rule_engine
from app.pipeline.extraction import ExtractedFieldData

router = APIRouter(prefix="/api/scans", tags=["audit"])


def _get_scan_or_404(scan_id: str, db: Session) -> models.Scan:
    scan = db.get(models.Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/audit", response_model=list[schemas.AuditLogOut])
def get_audit_trail(
    scan_id: str,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(auth.require_roles(ROLE_INSPECTOR, ROLE_DEPARTMENT_ADMIN)),
) -> list[models.AuditLog]:
    _get_scan_or_404(scan_id, db)
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.scan_id == scan_id)
        .order_by(models.AuditLog.created_at.asc())
        .all()
    )


@router.get("/{scan_id}/replay", response_model=schemas.ReplayOut)
def replay_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_user: models.User = Depends(auth.require_roles(ROLE_INSPECTOR, ROLE_DEPARTMENT_ADMIN)),
) -> schemas.ReplayOut:
    """Proves historical reproducibility live: re-evaluates a scan's ORIGINAL
    extracted fields against the EXACT rule-pack file (located by content hash,
    not by "whatever is active now") it was originally scored against, and
    reports whether the verdict reproduces exactly."""
    scan = _get_scan_or_404(scan_id, db)

    if not scan.rule_pack_hash:
        raise HTTPException(status_code=422, detail="This scan has no rule-pack hash to replay (it errored before evaluation)")

    original_pack = rule_engine.find_rule_pack_by_hash(settings.rule_pack_path.parent, scan.rule_pack_hash)
    if original_pack is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No rule-pack file on disk matches hash {scan.rule_pack_hash[:12]}… — the exact legal "
                "version this scan was evaluated under is no longer available for replay."
            ),
        )

    extracted_fields = {
        f.field_id: ExtractedFieldData(
            field_id=f.field_id,
            found=f.found,
            applicable=(f.found or any(e.field_id == f.field_id and e.status != "NOT_APPLICABLE" for e in scan.evaluations)),
            raw_value=f.raw_value,
            confidence=f.confidence,
            bbox=f.bbox,
        )
        for f in scan.fields
    }
    replayed_evaluations = rule_engine.evaluate_all(original_pack, extracted_fields, settings.confidence_threshold)
    replayed_verdict = rule_engine.aggregate_verdict(replayed_evaluations)

    return schemas.ReplayOut(
        scan_id=scan.id,
        original_rule_pack_version=scan.rule_pack_version,
        original_rule_pack_hash=scan.rule_pack_hash,
        original_overall_verdict=scan.overall_verdict,
        replayed_rule_pack_version=original_pack.version,
        replayed_rule_pack_hash=original_pack.sha256_hash,
        replayed_overall_verdict=replayed_verdict,
        reproduced=(replayed_verdict == scan.overall_verdict),
        evaluations=[
            schemas.RuleEvaluationOut(
                field_id=e.field_id,
                clause=e.clause,
                legal_reference=e.legal_reference,
                status=e.status,
                reason=e.reason,
                evidence=e.evidence,
                rule_pack_version=e.rule_pack_version,
            )
            for e in replayed_evaluations
        ],
    )
