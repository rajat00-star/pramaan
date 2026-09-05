"""Orchestrates one scan: image -> preprocessing -> detection -> OCR -> extraction
-> deterministic rule evaluation -> verdict. This is the only module that wires
the stages together; each stage stays independently swappable (see detection.py
and ocr.py for the documented extension points).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings
from app.pipeline import extraction, rule_engine
from app.pipeline.detection import FullImageDetector
from app.pipeline.errors import PramaanImageError, PramaanOCRError
from app.pipeline.extraction import ExtractedFieldData
from app.pipeline.ocr import OCRResult, TesseractOCREngine
from app.pipeline.preprocessing import load_and_preprocess
from app.pipeline.rule_engine import FieldEvaluation

logger = logging.getLogger("pramaan.pipeline")


@dataclass
class PipelineResult:
    status: str  # DONE | ERROR
    overall_verdict: str | None = None
    overall_confidence: float | None = None
    error_message: str | None = None

    ocr_result: OCRResult | None = None
    extracted_fields: dict[str, ExtractedFieldData] = field(default_factory=dict)
    rule_evaluations: list[FieldEvaluation] = field(default_factory=list)

    detector_method: str | None = None
    region_bbox: dict | None = None
    rule_pack_version: str | None = None
    rule_pack_hash: str | None = None


def _overall_confidence(extracted_fields: dict[str, ExtractedFieldData]) -> float | None:
    confidences = [f.confidence for f in extracted_fields.values() if f.applicable and f.confidence is not None]
    if not confidences:
        return None
    return sum(confidences) / len(confidences)


def run_pipeline(image_path: str | Path, settings: Settings) -> PipelineResult:
    try:
        preprocessed = load_and_preprocess(image_path)
    except PramaanImageError as exc:
        logger.exception("pipeline: image preprocessing failed for %s", image_path)
        return PipelineResult(status="ERROR", error_message=str(exc))

    detector = FullImageDetector()
    regions = detector.detect(preprocessed.enhanced)
    region = regions[0]

    try:
        ocr_engine = TesseractOCREngine(langs=settings.tesseract_langs)
        ocr_result = ocr_engine.run(region.image)
    except PramaanOCRError as exc:
        logger.exception("pipeline: OCR failed for %s", image_path)
        return PipelineResult(status="ERROR", error_message=str(exc), detector_method=region.method)

    if not ocr_result.full_text.strip():
        return PipelineResult(
            status="DONE",
            overall_verdict="REVIEW",
            overall_confidence=None,
            ocr_result=ocr_result,
            extracted_fields={},
            rule_evaluations=[],
            detector_method=region.method,
            region_bbox=region.bbox,
        )

    extracted_fields = extraction.extract_fields(ocr_result)
    rule_pack = rule_engine.load_rule_pack(str(settings.rule_pack_path))
    evaluations = rule_engine.evaluate_all(rule_pack, extracted_fields, settings.confidence_threshold)
    verdict = rule_engine.aggregate_verdict(evaluations)

    return PipelineResult(
        status="DONE",
        overall_verdict=verdict,
        overall_confidence=_overall_confidence(extracted_fields),
        ocr_result=ocr_result,
        extracted_fields=extracted_fields,
        rule_evaluations=evaluations,
        detector_method=region.method,
        region_bbox=region.bbox,
        rule_pack_version=rule_pack.version,
        rule_pack_hash=rule_pack.sha256_hash,
    )
