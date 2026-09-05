"""P0-2: run_pipeline() can fail in ways beyond PramaanImageError/PramaanOCRError,
and no failure — expected or unexpected — may leave a Scan stuck in PROCESSING,
return a raw 500, leak internals to the client, or go unlogged server-side.

Covers, per the task's checklist: Pillow DecompressionBombError, an unexpected
RuntimeError, an expected image error, an expected OCR error, and the successful
path (to prove we don't spuriously log errors when nothing went wrong).
"""

import logging

from PIL import Image

from app.config import get_settings
from app.pipeline.errors import PramaanOCRError
from app.pipeline.ocr import TesseractOCREngine
from app.routes import scan as scan_route

SAFE_GENERIC_MESSAGE_MARKERS = ("unexpected error", "try again")


def _assert_error_scan_is_safe_and_logged(response, caplog, *, forbidden_substrings=()):
    assert response.status_code == 201, response.text  # resource created; failure recorded in the body, not the status
    body = response.json()
    assert body["status"] == "ERROR"
    assert body["overall_verdict"] is None
    assert body["error_message"]
    for forbidden in forbidden_substrings:
        assert forbidden not in body["error_message"], f"leaked into client-facing message: {forbidden!r}"
    assert any(rec.exc_info for rec in caplog.records), "no traceback was logged server-side for this failure"
    return body


def test_unexpected_runtime_error_is_handled_gracefully(client, compliant_label_path, monkeypatch, caplog):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated unexpected pipeline crash — internal detail")

    monkeypatch.setattr(scan_route, "run_pipeline", _boom)

    with caplog.at_level(logging.INFO):
        with open(compliant_label_path, "rb") as f:
            response = client.post("/api/scans", files={"file": (compliant_label_path.name, f, "image/png")})

    body = _assert_error_scan_is_safe_and_logged(
        response, caplog, forbidden_substrings=("RuntimeError", "simulated unexpected pipeline crash")
    )
    assert any(marker in body["error_message"].lower() for marker in SAFE_GENERIC_MESSAGE_MARKERS)

    # Not stuck in PROCESSING — confirm via a fresh read, not just the POST response echo.
    refetched = client.get(f"/api/scans/{body['id']}").json()
    assert refetched["status"] == "ERROR"

    assert any("unexpected exception" in rec.message.lower() for rec in caplog.records)


def test_decompression_bomb_is_handled_gracefully(client, compliant_label_path, monkeypatch, caplog):
    # Lower Pillow's own bomb threshold so the ~1.26MP test fixture (1400x900) trips
    # it reliably (Pillow raises once pixels > 2x the configured limit).
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)

    with caplog.at_level(logging.INFO):
        with open(compliant_label_path, "rb") as f:
            response = client.post("/api/scans", files={"file": (compliant_label_path.name, f, "image/png")})

    body = _assert_error_scan_is_safe_and_logged(response, caplog, forbidden_substrings=("DecompressionBomb",))
    assert any(marker in body["error_message"].lower() for marker in SAFE_GENERIC_MESSAGE_MARKERS)
    assert any("unexpected exception" in rec.message.lower() for rec in caplog.records)


def test_expected_image_error_is_logged_and_does_not_leak_a_path(client, tmp_path, caplog):
    garbage_path = tmp_path / "not_an_image.png"
    garbage_path.write_bytes(b"this is not a real image file, just bytes")

    with caplog.at_level(logging.INFO):
        with open(garbage_path, "rb") as f:
            response = client.post("/api/scans", files={"file": ("not_an_image.png", f, "image/png")})

    upload_dir = str(get_settings().upload_dir)
    body = _assert_error_scan_is_safe_and_logged(response, caplog, forbidden_substrings=(upload_dir, str(tmp_path)))
    assert "corrupted" in body["error_message"].lower() or "not a supported image" in body["error_message"].lower()
    assert any("preprocessing failed" in rec.message.lower() for rec in caplog.records)


def test_expected_ocr_error_is_logged_and_handled(client, compliant_label_path, monkeypatch, caplog):
    def _boom(self, image):
        raise PramaanOCRError("simulated OCR engine failure")

    monkeypatch.setattr(TesseractOCREngine, "run", _boom)

    with caplog.at_level(logging.INFO):
        with open(compliant_label_path, "rb") as f:
            response = client.post("/api/scans", files={"file": (compliant_label_path.name, f, "image/png")})

    body = _assert_error_scan_is_safe_and_logged(response, caplog)
    assert body["error_message"] == "simulated OCR engine failure"
    assert any("ocr failed" in rec.message.lower() for rec in caplog.records)


def test_successful_pipeline_logs_no_errors(client, compliant_label_path, caplog):
    with caplog.at_level(logging.INFO):
        with open(compliant_label_path, "rb") as f:
            response = client.post("/api/scans", files={"file": (compliant_label_path.name, f, "image/png")})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "DONE"
    assert body["overall_verdict"] == "COMPLIANT"

    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records == [], f"unexpected error-level logs on the happy path: {[r.message for r in error_records]}"
