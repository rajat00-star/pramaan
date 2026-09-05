from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExtractedFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    found: bool
    raw_value: str | None
    confidence: float | None
    bbox: dict | None
    source: str


class RuleEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    clause: str
    legal_reference: str
    status: str
    reason: str
    evidence: dict | None
    rule_pack_version: str


class ReviewCorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    original_value: str | None
    corrected_value: str
    reviewer: str
    note: str | None
    previous_verdict: str | None
    resulting_verdict: str | None
    created_at: datetime


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str | None
    image_path: str
    status: str
    error_message: str | None

    detector_method: str | None
    ocr_engine: str | None
    ocr_lang: str | None
    raw_ocr_text: str | None
    ocr_mean_confidence: float | None

    rule_pack_version: str | None
    rule_pack_hash: str | None

    overall_verdict: str | None
    overall_confidence: float | None

    created_at: datetime
    updated_at: datetime

    fields: list[ExtractedFieldOut]
    evaluations: list[RuleEvaluationOut]
    reviews: list[ReviewCorrectionOut]


class ScanSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str | None
    status: str
    overall_verdict: str | None
    overall_confidence: float | None
    created_at: datetime


class ReviewCorrectionIn(BaseModel):
    field_id: str
    corrected_value: str
    note: str | None = None
    # No `reviewer` field: identity always comes from the authenticated user
    # server-side (see routes/review.py) — a client-supplied identity field is
    # exactly what made the old reviewer-name field XSS-exploitable.


class RulePackFieldOut(BaseModel):
    field_id: str
    clause: str
    title: str
    legal_reference: str


class RulePackOut(BaseModel):
    rule_pack_version: str
    effective_date: str
    sha256_hash: str
    scope: str
    fields: list[RulePackFieldOut]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    actor_user_id: str | None
    payload: dict | None
    created_at: datetime


class ReplayOut(BaseModel):
    scan_id: str
    original_rule_pack_version: str | None
    original_rule_pack_hash: str | None
    original_overall_verdict: str | None
    replayed_rule_pack_version: str | None
    replayed_rule_pack_hash: str | None
    replayed_overall_verdict: str | None
    reproduced: bool
    evaluations: list[RuleEvaluationOut]


class DashboardSummaryOut(BaseModel):
    total_scans: int
    compliant: int
    non_compliant: int
    review: int
    error: int
    pending_review_count: int
    mean_confidence: float | None
    violation_frequency: dict[str, int]  # field_id -> count of FAIL across all scans
    recent_scans: list[ScanSummaryOut]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
