"""Regression tests for two bugs found during a real-world validation pass using
actual camera photographs of real packaged products (not synthetic fixtures).

1. EXIF orientation was never applied before OCR. Real iPhone photos store an
   EXIF orientation tag rather than rotating pixel data; skipping it turned two
   correctly-oriented real photos into ~0%-useful-text OCR garbage. Verified
   directly against the real photos before fixing (see conversation record);
   this test reproduces the same bug class with a self-contained synthetic
   image so it doesn't depend on external files.

2. Tesseract's default page-segmentation mode (PSM 3) returned completely empty
   text on some real product photos where PSM 11 ("sparse text") recovered
   real content. `TesseractOCREngine.run()` now retries with PSM 11 only when
   the default pass finds nothing.
"""

from PIL import Image

from app.pipeline.ocr import TesseractOCREngine
from app.pipeline.preprocessing import load_and_preprocess
from tests.conftest import COMPLIANT_LABEL_LINES, render_label


def _render_rotated_jpeg_with_exif_orientation(lines: list[str], path, rotate_degrees: int, exif_orientation: int):
    """Simulate a phone photo: render text normally, physically rotate the pixel
    data (as a camera sensor might capture landscape while held in portrait),
    then tag it with the EXIF orientation a real phone would use to say
    'rotate this back for display' — without actually rotating the pixels."""
    render_label(lines, path.with_suffix(".tmp.png"))
    img = Image.open(path.with_suffix(".tmp.png"))
    rotated = img.rotate(rotate_degrees, expand=True)

    exif = Image.Exif()
    exif[274] = exif_orientation  # 274 = the standard EXIF "Orientation" tag id
    rotated.convert("RGB").save(path, "JPEG", exif=exif)
    path.with_suffix(".tmp.png").unlink(missing_ok=True)
    return path


def test_exif_rotated_photo_is_corrected_before_ocr(tmp_path):
    # Orientation 6 means "the stored pixels are rotated 90° CW from how they
    # should display; rotate 90° CW to fix" — exactly what both real iPhone
    # photos in the validation pass carried.
    jpeg_path = _render_rotated_jpeg_with_exif_orientation(
        COMPLIANT_LABEL_LINES, tmp_path / "rotated.jpg", rotate_degrees=90, exif_orientation=6
    )

    preprocessed = load_and_preprocess(jpeg_path)
    ocr_result = TesseractOCREngine(langs="eng").run(preprocessed.enhanced)

    # If EXIF orientation weren't corrected, this would OCR as unreadable noise
    # (verified directly on real photos before the fix) instead of real words.
    assert "Manufactured" in ocr_result.full_text
    assert "Sunflower" in ocr_result.full_text


def test_preprocessing_normalizes_exif_orientation_dimensions(tmp_path):
    jpeg_path = _render_rotated_jpeg_with_exif_orientation(
        COMPLIANT_LABEL_LINES, tmp_path / "rotated2.jpg", rotate_degrees=90, exif_orientation=6
    )
    preprocessed = load_and_preprocess(jpeg_path)
    # The original render_label canvas is wider than tall (1400x900); after a
    # genuine phone-style 90°-stored-plus-EXIF-correction round trip, the
    # corrected image should be back to that same (wide) orientation.
    assert preprocessed.original.width > preprocessed.original.height


def test_ocr_falls_back_to_sparse_text_mode_when_default_pass_is_empty(monkeypatch):
    """A blank/near-blank image (as some real low-resolution product photos
    produced with Tesseract's default PSM) should still get a genuine second
    attempt rather than silently returning nothing."""
    engine = TesseractOCREngine(langs="eng")
    call_configs = []
    real_run_pass = engine._run_pass

    def _tracking_run_pass(image, config=""):
        call_configs.append(config)
        return real_run_pass(image, config=config)

    monkeypatch.setattr(engine, "_run_pass", _tracking_run_pass)

    blank_image = Image.new("RGB", (400, 400), "white")
    result = engine.run(blank_image)

    assert call_configs == ["", "--psm 11"]  # default pass, then the sparse-text fallback
    assert result.full_text.strip() == ""  # a genuinely blank image still has nothing to find
    assert result.psm_used == "--psm 11"  # confirms the fallback pass's result was what got returned


def test_ocr_does_not_fall_back_when_default_pass_finds_text(monkeypatch):
    """The fallback must not run (and cannot degrade results) when the default
    pass already found something — verified during validation that PSM 11 is
    sometimes noisier than the default on images that already work."""
    engine = TesseractOCREngine(langs="eng")
    call_configs = []
    real_run_pass = engine._run_pass

    def _tracking_run_pass(image, config=""):
        call_configs.append(config)
        return real_run_pass(image, config=config)

    monkeypatch.setattr(engine, "_run_pass", _tracking_run_pass)

    img = Image.new("RGB", (1400, 900), "white")
    from PIL import ImageDraw

    from tests.conftest import _load_font

    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "Manufactured by: Test Co", fill="black", font=_load_font(28))

    result = engine.run(img)

    assert call_configs == [""]  # default pass only — no fallback triggered
    assert "Manufactured" in result.full_text
