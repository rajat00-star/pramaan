from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import Settings, get_settings
from app.db import get_db
from app.models import ROLE_DEPARTMENT_ADMIN, ROLE_INSPECTOR
from app.pipeline import rule_engine

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=schemas.DashboardSummaryOut)
def dashboard_summary(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _current_user: models.User = Depends(auth.require_roles(ROLE_INSPECTOR, ROLE_DEPARTMENT_ADMIN)),
) -> schemas.DashboardSummaryOut:
    total_scans = db.query(func.count(models.Scan.id)).scalar() or 0

    def _count(verdict: str | None = None, status: str | None = None) -> int:
        q = db.query(func.count(models.Scan.id))
        if verdict is not None:
            q = q.filter(models.Scan.overall_verdict == verdict)
        if status is not None:
            q = q.filter(models.Scan.status == status)
        return q.scalar() or 0

    mean_confidence = db.query(func.avg(models.Scan.overall_confidence)).filter(
        models.Scan.overall_confidence.isnot(None)
    ).scalar()

    violation_rows = (
        db.query(models.RuleEvaluation.field_id, func.count(models.RuleEvaluation.id))
        .filter(models.RuleEvaluation.status == "FAIL")
        .group_by(models.RuleEvaluation.field_id)
        .all()
    )

    recent_scans = db.query(models.Scan).order_by(models.Scan.created_at.desc()).limit(10).all()

    activity_rows = (
        db.query(
            models.ReviewCorrection.reviewer,
            func.count(models.ReviewCorrection.id),
            func.max(models.ReviewCorrection.created_at),
        )
        .group_by(models.ReviewCorrection.reviewer)
        .order_by(func.count(models.ReviewCorrection.id).desc())
        .all()
    )
    inspector_activity = [
        schemas.InspectorActivityOut(reviewer=reviewer, review_count=count, last_review_at=last_at)
        for reviewer, count, last_at in activity_rows
    ]

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    reviews_today = (
        db.query(func.count(models.ReviewCorrection.id))
        .filter(models.ReviewCorrection.created_at >= today_start)
        .scalar()
        or 0
    )

    rule_pack = rule_engine.load_rule_pack(str(settings.rule_pack_path))

    return schemas.DashboardSummaryOut(
        total_scans=total_scans,
        compliant=_count(verdict="COMPLIANT"),
        non_compliant=_count(verdict="NON_COMPLIANT"),
        review=_count(verdict="REVIEW"),
        error=_count(status="ERROR"),
        pending_review_count=_count(verdict="REVIEW"),
        mean_confidence=float(mean_confidence) if mean_confidence is not None else None,
        violation_frequency=dict(violation_rows),
        recent_scans=recent_scans,
        inspector_activity=inspector_activity,
        reviews_today=reviews_today,
        rule_pack=schemas.RulePackSummaryOut(
            rule_pack_version=rule_pack.version,
            effective_date=rule_pack.effective_date,
            sha256_hash=rule_pack.sha256_hash,
            field_count=len(rule_pack.fields),
        ),
    )
