"""Real Tesseract Hindi OCR + Hindi keyword extraction — not a mocked claim.

This is an HONEST PARTIAL step toward the deck's multilingual requirement: it
proves Hindi (Devanagari) keyword recognition genuinely works end-to-end
through real OCR, using `tests/fixtures/hindi_label.png` (rendered with a real
Devanagari system font, not hand-typed Unicode fed straight to the parser).

It does NOT claim full multilingual support. Measured directly while building
this: Devanagari *keyword* text recognizes reliably, but Latin *digits* mixed
into the same image (a phone number, a price) are measurably less reliable
than in a pure-English label — this test only asserts what was actually
verified, not what would be nice to be true.
"""

import pytesseract
from PIL import Image

from app.pipeline.extraction import extract_fields
from app.pipeline.ocr import TesseractOCREngine


def test_tesseract_has_hindi_language_data_installed():
    langs = pytesseract.get_languages()
    assert "hin" in langs, "Hindi language data not installed — run `brew install tesseract-lang`"


def test_hindi_label_keywords_are_extracted_via_real_ocr(hindi_label_path):
    image = Image.open(hindi_label_path)
    ocr_result = TesseractOCREngine(langs="hin+eng").run(image)

    assert ocr_result.full_text.strip() != ""

    fields = extract_fields(ocr_result)

    assert fields["manufacturer_packer_importer"].found
    assert "टेस्ट कंपनी" in fields["manufacturer_packer_importer"].raw_value

    assert fields["common_generic_name"].found
    assert "तेल" in fields["common_generic_name"].raw_value  # "oil"

    assert fields["net_quantity"].found
    assert "500" in fields["net_quantity"].raw_value and "g" in fields["net_quantity"].raw_value

    assert fields["retail_sale_price"].found  # digit accuracy not asserted — see module docstring

    assert fields["consumer_care_details"].found


def test_english_only_ocr_does_not_find_hindi_keywords_without_hindi_language_pack(hindi_label_path):
    # Documents the real dependency: Hindi keyword extraction only works when the
    # OCR engine is actually configured with the Hindi language model.
    image = Image.open(hindi_label_path)
    ocr_result = TesseractOCREngine(langs="eng").run(image)
    fields = extract_fields(ocr_result)
    # English-only Tesseract garbles Devanagari script into noise it can't anchor
    # keywords in — this is expected, not a bug, and is why TESSERACT_LANGS must
    # include "hin" for Hindi labels (see .env.example).
    assert not fields["manufacturer_packer_importer"].found
