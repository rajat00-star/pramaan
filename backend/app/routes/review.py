from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import Settings, get_settings
from app.db import get_db
from app.models import ROLE_DEPARTMENT_ADMIN, ROLE_INSPECTOR
from app.pipeline import rule_engine
from app.pipeline.extraction import ExtractedFieldData

router = APIRouter(prefix="/api/scans", tags=["review"])


@router.post("/{scan_id}/review", response_model=schemas.ScanOut)
def submit_review(
    scan_id: str,
    payload: schemas.ReviewCorrectionIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: models.User = Depends(auth.require_roles(ROLE_INSPECTOR, ROLE_DEPARTMENT_ADMIN)),
) -> models.Scan:
    scan = db.get(models.Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    extracted_field = next((f for f in scan.fields if f.field_id == payload.field_id), None)
    if extracted_field is None:
        raise HTTPException(status_code=404, detail=f"Field '{payload.field_id}' not found on this scan")

    rule_pack = rule_engine.load_rule_pack(str(settings.rule_pack_path))
    if scan.rule_pack_version and scan.rule_pack_version != rule_pack.version:
        # Re-evaluate against the version the scan was ORIGINALLY made with, not today's
        # live rule pack — a historical verdict must stay reproducible from its own inputs.
        raise HTTPException(
            status_code=409,
            detail=(
                f"Rule pack has changed since this scan was made (scan used v{scan.rule_pack_version}, "
                f"live is v{rule_pack.version}). Re-evaluating a scan against a newer rule-pack "
                "version is not supported by this endpoint."
            ),
        )

    field_spec = rule_pack.fields_by_id().get(payload.field_id)
    if field_spec is None:
        raise HTTPException(status_code=500, detail=f"Field '{payload.field_id}' is not defined in the rule pack")

    original_value = extracted_field.raw_value
    previous_verdict = scan.overall_verdict

    # Reviewer identity always comes from the authenticated session, never from
    # client-supplied request body text — see schemas.ReviewCorrectionIn.
    db.add(
        models.ReviewCorrection(
            scan_id=scan.id,
            field_id=payload.field_id,
            original_value=original_value,
            corrected_value=payload.corrected_value,
            reviewer_user_id=current_user.id,
            reviewer=current_user.username,
            note=payload.note,
            previous_verdict=previous_verdict,
        )
    )

    # The original OCR/extraction value is preserved unconditionally: `original_value`
    # above already captured it before this overwrite, and it lives on permanently in
    # the ReviewCorrection audit row even though the live ExtractedField row below is
    # updated to reflect the human-verified value going forward.
    extracted_field.raw_value = payload.corrected_value
    extracted_field.confidence = 100.0
    extracted_field.found = True
    extracted_field.source = "human_review"

    updated_extracted = ExtractedFieldData(
        field_id=payload.field_id,
        found=True,
        applicable=True,
        raw_value=payload.corrected_value,
        confidence=100.0,
        bbox=extracted_field.bbox,
    )
    new_eval = rule_engine.evaluate_field(field_spec, updated_extracted, settings.confidence_threshold, rule_pack.version)

    existing_eval = next((e for e in scan.evaluations if e.field_id == payload.field_id), None)
    if existing_eval:
        existing_eval.status = new_eval.status
        existing_eval.reason = new_eval.reason
        existing_eval.evidence = new_eval.evidence
    else:
        db.add(
            models.RuleEvaluation(
                scan_id=scan.id,
                field_id=new_eval.field_id,
                clause=new_eval.clause,
                legal_reference=new_eval.legal_reference,
                status=new_eval.status,
                reason=new_eval.reason,
                evidence=new_eval.evidence,
                rule_pack_version=new_eval.rule_pack_version,
            )
        )

    db.flush()
    db.refresh(scan)
    scan.overall_verdict = rule_engine.aggregate_verdict_from_statuses([e.status for e in scan.evaluations])

    db.add(
        models.AuditLog(
            scan_id=scan.id,
            event_type="FIELD_CORRECTED",
            actor_user_id=current_user.id,
            payload={
                "field_id": payload.field_id,
                "original_value": original_value,
                "corrected_value": payload.corrected_value,
                "reviewer": current_user.username,
                "new_field_status": new_eval.status,
            },
        )
    )
    if previous_verdict != scan.overall_verdict:
        db.add(
            models.AuditLog(
                scan_id=scan.id,
                event_type="VERDICT_CHANGED",
                actor_user_id=current_user.id,
                payload={"from": previous_verdict, "to": scan.overall_verdict, "caused_by_field": payload.field_id},
            )
        )

    # Record the resulting verdict on the same ReviewCorrection row we just added —
    # flush() above already assigned it an id, so fetch it back to update in place.
    db.query(models.ReviewCorrection).filter_by(scan_id=scan.id, field_id=payload.field_id).order_by(
        models.ReviewCorrection.id.desc()
    ).first().resulting_verdict = scan.overall_verdict

    db.commit()
    db.refresh(scan)
    return scan
