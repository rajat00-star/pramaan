import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ROLE_CITIZEN = "citizen"
ROLE_INSPECTOR = "inspector"
ROLE_DEPARTMENT_ADMIN = "department_admin"
ALL_ROLES = (ROLE_CITIZEN, ROLE_INSPECTOR, ROLE_DEPARTMENT_ADMIN)


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """An authenticated account. Role drives server-side authorization everywhere —
    never inferred from the frontend, never trusted from client-supplied input."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), index=True)  # citizen | inspector | department_admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    scans: Mapped[list["Scan"]] = relationship(back_populates="owner")


class Scan(Base):
    """One end-to-end run of the pipeline against one uploaded image."""

    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_status_created_at", "status", "created_at"),
        Index("ix_scans_verdict_created_at", "overall_verdict", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    image_path: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default="PROCESSING", index=True)  # PROCESSING | DONE | ERROR
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    detector_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocr_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocr_lang: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_mean_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    rule_pack_version: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    rule_pack_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    overall_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)  # COMPLIANT|NON_COMPLIANT|REVIEW
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    owner: Mapped["User | None"] = relationship(back_populates="scans")
    fields: Mapped[list["ExtractedField"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    evaluations: Mapped[list["RuleEvaluation"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    reviews: Mapped[list["ReviewCorrection"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class ExtractedField(Base):
    """One rule_pack field as extracted (or not found) from OCR output for a given scan."""

    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"))
    field_id: Mapped[str] = mapped_column(String(64))
    found: Mapped[bool] = mapped_column(default=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {left, top, width, height}
    source: Mapped[str] = mapped_column(String(16), default="ocr")  # ocr | human_review

    scan: Mapped["Scan"] = relationship(back_populates="fields")


class RuleEvaluation(Base):
    """Deterministic verdict for one field against one version of rule_pack.json."""

    __tablename__ = "rule_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"))
    field_id: Mapped[str] = mapped_column(String(64))
    clause: Mapped[str] = mapped_column(String(128))
    legal_reference: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))  # PASS | FAIL | REVIEW | NOT_APPLICABLE
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rule_pack_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    scan: Mapped["Scan"] = relationship(back_populates="evaluations")


class ReviewCorrection(Base):
    """Human-in-the-loop correction of a field: BEFORE/AFTER/WHY/WHO/WHEN, plus the
    verdict transition it caused. Immutable — never updated or deleted, only appended.
    `reviewer` is always the authenticated user's username, set server-side (never
    taken from client-supplied free text — that was the original XSS vector)."""

    __tablename__ = "review_corrections"
    __table_args__ = (Index("ix_review_corrections_scan_id_created_at", "scan_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"))
    field_id: Mapped[str] = mapped_column(String(64))
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str] = mapped_column(Text)
    reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer: Mapped[str] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    resulting_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    scan: Mapped["Scan"] = relationship(back_populates="reviews")


class AuditLog(Base):
    """Append-only trail of everything that happened to a scan. Never updated or
    deleted by application code — only ever inserted."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_scan_id_created_at", "scan_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"))
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    scan: Mapped["Scan"] = relationship(back_populates="audit_logs")
