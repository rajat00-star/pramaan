"""Heuristic field extraction from raw OCR text.

This is a deterministic, keyword-anchored regex parser — it stands in for the
layout-aware structuring (LayoutLM-style) the architecture calls for. It only
ever pulls text out of the OCR result; it never judges whether that text is
legally compliant (that is the rule engine's job, kept strictly separate). It
is intentionally brittle on real-world unlabelled packaging (a plain product
name with no "Product:" prefix, e.g.) — that gap is exactly what layout-aware
ML is future work for, not something to fake here.

Keyword patterns include common Hindi (Devanagari) equivalents alongside the
English ones, real-tested against Tesseract's `hin`/`hin+eng` models (see
tests/test_multilingual_extraction.py). This is an HONEST, PARTIAL step toward
the architecture's multilingual requirement, not full coverage: only these
seven field-anchor phrases are covered, only in Hindi, and mixed Devanagari +
Latin-numeral OCR (e.g. "500 g" printed next to Hindi text) is measurably less
reliable than pure-English labels — verified directly, not assumed. The other
languages Tesseract has installed (Bengali, Gujarati, Kannada, Marathi,
Punjabi, Tamil, Telugu) have no keyword coverage at all yet.
"""

import re
from dataclasses import dataclass

from app.pipeline.ocr import OCRResult, Word

_LINE_VALUE = r"([^\n]+)"

FIELD_KEYWORDS: dict[str, str] = {
    "manufacturer_packer_importer": (
        r"(?:Manufactured\s+by|Mfd\.?\s+by|Packed\s+by|Marketed\s+by|Manufacturer|निर्माता|उत्पादक)\s*[:\-]?\s*"
    ),
    "common_generic_name": r"(?:Product|Commodity|Contents|उत्पाद|वस्तु)\s*[:\-]?\s*",
    "net_quantity": (
        r"(?:Net\s*(?:Wt|Weight|Qty|Quantity|Vol|Volume)\.?|शुद्ध\s*वजन|निवल\s*मात्रा|मात्रा)\s*[:\-]?\s*"
    ),
    "date_of_manufacture": (
        r"(?:Mfg\.?\s*Date|Manufactured\s+on|Pkd\.?\s+on|Packed\s+on|Mfd\.?\s+on|निर्माण\s*तिथि|उत्पादन\s*तिथि)\s*[:\-]?\s*"
    ),
    "retail_sale_price": r"(?:MRP|Maximum\s+Retail\s+Price|अधिकतम\s*खुदरा\s*मूल्य)\s*[:\-]?\s*",
    "consumer_care_details": (
        r"(?:Customer\s+Care|Consumer\s+Care|For\s+complaints|Complaints?|ग्राहक\s*सेवा|उपभोक्ता\s*सेवा)\s*[:\-]?\s*"
    ),
    "country_of_origin": r"(?:Country\s+of\s+Origin|Made\s+in|Origin|मूल\s*देश)\s*[:\-]?\s*",
}

# Signals that a product is imported, which is what makes Rule 6(1)(aa) applicable at all.
IMPORTED_SIGNAL_RE = re.compile(r"country\s+of\s+origin|imported\s+by|made\s+in\s+|मूल\s*देश", re.IGNORECASE)

# Real MRP boxes commonly print the amount and the "inclusive of all taxes"
# clause as two separate physical lines (the amount on one line, the clause
# wrapped to the next) rather than one sentence — verified directly on a real
# product photo (Tata Tea Premium), where "MRP Rs. 170.00" and "(inclusive of
# all taxes)" are consecutive OCR lines. Without this, the line-anchored
# capture only ever sees the first line and the rule engine FAILs a genuinely
# compliant declaration for "not stating inclusive of all taxes" — a false
# NON_COMPLIANT verdict against a real compliant product. Deliberately narrow
# (must be the ENTIRE next line, nothing else) so it only absorbs a clause
# that is clearly its own continuation, not an unrelated nearby line.
_INCLUSIVE_TAXES_CONTINUATION_RE = re.compile(
    r"^\s*\(?\s*incl(?:usive|\.)?\s+(?:of\s+)?all\s+taxes\s*\)?\s*$", re.IGNORECASE
)


def _retail_price_continuation_span(full_text: str, value_end: int) -> tuple[str, int] | None:
    """If the line immediately after the captured MRP line is wholly the
    "(inclusive of all taxes)" clause, return its text and end offset so the
    caller can fold it into the same declaration — otherwise None."""
    if value_end >= len(full_text) or full_text[value_end] != "\n":
        return None
    line_start = value_end + 1
    line_end = full_text.find("\n", line_start)
    if line_end == -1:
        line_end = len(full_text)
    next_line = full_text[line_start:line_end]
    if _INCLUSIVE_TAXES_CONTINUATION_RE.match(next_line):
        return next_line.strip(), line_end
    return None

# Anchored to the start of a line (allowing leading whitespace) — NOT a bare
# `search()` over the whole text. Found via real-world validation: an unanchored
# "Product"/"Commodity" pattern matched the ordinary English word "product"
# inside unrelated warning prose ("If the product enters the eye, rinse with
# water...") and confidently extracted the rest of that sentence as the
# declared common/generic name. Real labels declare each field on its own
# line, so requiring the keyword to be the first thing on a line is both more
# accurate to how labels are actually printed and closes this false-positive.
_COMPILED_KEYWORDS = {
    field_id: re.compile(r"^\s*" + pattern + _LINE_VALUE, re.IGNORECASE | re.MULTILINE)
    for field_id, pattern in FIELD_KEYWORDS.items()
}


@dataclass
class ExtractedFieldData:
    field_id: str
    found: bool
    applicable: bool = True
    raw_value: str | None = None
    confidence: float | None = None
    bbox: dict | None = None


def _words_in_span(ocr_result: OCRResult, start: int, end: int) -> list[Word]:
    return [
        word
        for word, (span_start, span_end) in zip(ocr_result.words, ocr_result.word_spans, strict=True)
        if span_start < end and span_end > start
    ]


def _has_substantive_content(value: str) -> bool:
    """A real declaration always has at least one letter or digit. Guards against
    a genuine bug found via real-world validation: a multi-column label layout
    (value in an adjacent column, not the same OCR line as its keyword) can leave
    nothing but trailing punctuation after the keyword — e.g. "Net Qty," with the
    real "510 g" value elsewhere in the OCR stream. Treating that punctuation-only
    capture as a found value let the rule engine FAIL a compliant product for
    "not stating a recognised unit", when the truth is extraction found nothing
    at all. Not found is always REVIEW, never a confident wrong FAIL."""
    return any(ch.isalnum() for ch in value)


def _confidence_and_bbox(words: list[Word]) -> tuple[float | None, dict | None]:
    if not words:
        return None, None
    confidences = [w.confidence for w in words if w.confidence >= 0]
    confidence = sum(confidences) / len(confidences) if confidences else None
    left = min(w.left for w in words)
    top = min(w.top for w in words)
    right = max(w.left + w.width for w in words)
    bottom = max(w.top + w.height for w in words)
    bbox = {"left": left, "top": top, "width": right - left, "height": bottom - top}
    return confidence, bbox


def extract_fields(ocr_result: OCRResult) -> dict[str, ExtractedFieldData]:
    results: dict[str, ExtractedFieldData] = {}

    is_imported = bool(IMPORTED_SIGNAL_RE.search(ocr_result.full_text))

    for field_id, pattern in _COMPILED_KEYWORDS.items():
        if field_id == "country_of_origin" and not is_imported:
            results[field_id] = ExtractedFieldData(field_id=field_id, found=False, applicable=False)
            continue

        match = pattern.search(ocr_result.full_text)
        if not match or not _has_substantive_content(match.group(1)):
            results[field_id] = ExtractedFieldData(field_id=field_id, found=False, applicable=True)
            continue

        raw_value = match.group(1).strip()
        value_start, value_end = match.span(1)

        if field_id == "retail_sale_price" and "incl" not in raw_value.lower():
            continuation = _retail_price_continuation_span(ocr_result.full_text, value_end)
            if continuation is not None:
                continuation_text, value_end = continuation
                raw_value = f"{raw_value} {continuation_text}"

        words = _words_in_span(ocr_result, value_start, value_end)
        confidence, bbox = _confidence_and_bbox(words)

        results[field_id] = ExtractedFieldData(
            field_id=field_id,
            found=True,
            applicable=True,
            raw_value=raw_value,
            confidence=confidence,
            bbox=bbox,
        )

    return results
