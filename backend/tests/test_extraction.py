import pytest

from app.pipeline.extraction import extract_fields
from app.pipeline.ocr import OCRResult, Word


def make_ocr_result(lines: list[str], confidence: float = 90.0) -> OCRResult:
    """Build a synthetic OCRResult without touching Tesseract — fast, deterministic
    unit tests for the extraction regexes and bbox/confidence mapping logic."""
    words: list[Word] = []
    spans: list[tuple[int, int]] = []
    full_text = ""
    for line_idx, line in enumerate(lines):
        for tok in line.split(" "):
            if full_text and not full_text.endswith("\n"):
                full_text += " "
            start = len(full_text)
            full_text += tok
            end = len(full_text)
            spans.append((start, end))
            words.append(
                Word(text=tok, confidence=confidence, left=start * 10, top=line_idx * 40, width=len(tok) * 10, height=30, line_id=(1, 1, line_idx))
            )
        full_text += "\n"
    return OCRResult(full_text=full_text, words=words, word_spans=spans, engine="test", lang="eng", mean_confidence=confidence)


def test_manufacturer_field_extracted_with_confidence_and_bbox():
    fields = extract_fields(make_ocr_result(["Manufactured by: Acme Foods Pvt Ltd, Delhi"]))
    f = fields["manufacturer_packer_importer"]
    assert f.found
    assert "Acme Foods" in f.raw_value
    assert f.confidence == pytest.approx(90.0)
    assert f.bbox is not None
    assert f.bbox["width"] > 0


def test_missing_field_returns_not_found_with_no_value():
    fields = extract_fields(make_ocr_result(["Product: Refined Oil"]))
    f = fields["manufacturer_packer_importer"]
    assert f.found is False
    assert f.raw_value is None
    assert f.confidence is None


def test_country_of_origin_not_applicable_without_import_signal():
    fields = extract_fields(make_ocr_result(["Product: Refined Oil", "Net Wt: 900 g"]))
    assert fields["country_of_origin"].applicable is False
    assert fields["country_of_origin"].found is False


def test_country_of_origin_applicable_and_extracted_when_imported():
    fields = extract_fields(make_ocr_result(["Country of Origin: China", "Product: Toy Car"]))
    f = fields["country_of_origin"]
    assert f.applicable is True
    assert f.found is True
    assert "China" in f.raw_value


def test_net_quantity_raw_value_captures_number_and_unit():
    fields = extract_fields(make_ocr_result(["Net Wt: 900 g"]))
    assert fields["net_quantity"].raw_value.strip() == "900 g"


def test_retail_sale_price_captures_full_line_for_inclusive_check():
    fields = extract_fields(make_ocr_result(["MRP Rs. 150.00 incl. of all taxes"]))
    assert "incl" in fields["retail_sale_price"].raw_value.lower()


def test_retail_sale_price_folds_in_inclusive_of_taxes_clause_from_next_line():
    """Regression test for a real false-NON_COMPLIANT bug found via real-world
    validation: a real, physically compliant product (Tata Tea Premium) prints
    "MRP Rs. 170.00" and "(inclusive of all taxes)" as two separate lines. The
    line-anchored capture only saw the first line, so the rule engine FAILed a
    genuinely compliant MRP declaration for "not stating inclusive of all
    taxes" -- verified live against the real photo before this fix existed."""
    fields = extract_fields(make_ocr_result(["MRP Rs. 170.00", "(inclusive of all taxes)"]))
    f = fields["retail_sale_price"]
    assert f.found is True
    assert "incl" in f.raw_value.lower()


def test_retail_sale_price_does_not_fold_in_an_unrelated_next_line():
    """The continuation must be the ENTIRE next line, not just any line
    containing "incl" somewhere -- an unrelated line must never be silently
    absorbed into the price declaration."""
    fields = extract_fields(make_ocr_result(["MRP Rs. 150.00", "Store in a cool, dry place, inclusive"]))
    f = fields["retail_sale_price"]
    assert f.found is True
    assert "incl" not in f.raw_value.lower()


def test_net_quantity_does_not_report_found_for_punctuation_only_value():
    """Regression test for a real false-NON_COMPLIANT bug found via real-world
    validation: a multi-column label (e.g. MyFitness peanut butter) had "Net
    Qty," on its own OCR line with the real "510 g" value scrambled into an
    adjacent column, not that line. This must be REVIEW (not found), never a
    confident FAIL for "no recognised unit" against a value that was never a
    real declaration in the first place."""
    fields = extract_fields(make_ocr_result(["Net Qty,", "Expiry - f", "Batch No,"]))
    assert fields["net_quantity"].found is False
    # Note: "MRP/USPR ." is deliberately not asserted here — "USPR" is genuine
    # alphanumeric content (leaked adjacent label text, not punctuation), so it's
    # correctly still "found"; that case is instead caught by confidence gating
    # (verified live: it scored 19% confidence and was correctly routed to REVIEW).


def test_common_generic_name_does_not_match_the_word_product_mid_sentence():
    """Regression test for a real false-positive found via real-world validation:
    the ordinary English word "product" appearing inside unrelated warning prose
    ("If the product enters the eye, rinse with water...") was previously
    extracted as if it were the declared common/generic name, because the
    keyword search wasn't anchored to the start of a line."""
    fields = extract_fields(
        make_ocr_result(
            [
                "WARNING: Keep away from the eyes. If the product enters the eye, rinse with",
                "water. If irritation persists, consult a doctor.",
            ]
        )
    )
    assert fields["common_generic_name"].found is False


def test_common_generic_name_still_matches_when_keyword_starts_the_line():
    fields = extract_fields(make_ocr_result(["Product: Refined Sunflower Oil"]))
    assert fields["common_generic_name"].found is True
    assert "Refined Sunflower Oil" in fields["common_generic_name"].raw_value


def test_all_seven_field_ids_always_present_in_result():
    fields = extract_fields(make_ocr_result(["garbled unrelated text with no keywords"]))
    assert set(fields) == {
        "manufacturer_packer_importer",
        "country_of_origin",
        "common_generic_name",
        "net_quantity",
        "date_of_manufacture",
        "retail_sale_price",
        "consumer_care_details",
    }
