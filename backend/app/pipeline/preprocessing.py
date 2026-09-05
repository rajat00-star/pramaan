from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.pipeline.errors import PramaanImageError


@dataclass
class PreprocessedImage:
    original: Image.Image  # untouched, used for evidence crops shown to the user
    enhanced: Image.Image  # contrast/denoise-corrected, used for OCR


def load_and_preprocess(image_path: str | Path) -> PreprocessedImage:
    """Open an uploaded file and produce an OCR-friendly version of it.

    Real-world label photos suffer from glare, low contrast and mild noise; this
    applies grayscale conversion, denoising and adaptive contrast (CLAHE) which
    measurably helps Tesseract without needing a trained model. Deskew/perspective
    correction is intentionally not attempted here — deferred until a real label
    detector (YOLOv8) supplies the four corners of the label to warp against; the
    real-camera-photo failures actually observed in validation did not need it
    once EXIF orientation (below) was corrected.
    """
    try:
        with Image.open(image_path) as img:
            img.verify()
        original = Image.open(image_path)
        original.load()
        # Phone cameras (confirmed: iPhone) commonly store photos with the sensor's
        # raw orientation plus an EXIF tag saying how to rotate for display, rather
        # than rotating the pixel data itself. Every downstream step here — CLAHE,
        # OCR, bounding boxes — operates on raw pixels, so skipping this turns a
        # correctly-oriented photo into unreadable, rotated noise for OCR. Verified
        # directly: two real 90°-rotated iPhone photos went from ~0% useful OCR
        # text to fully readable label text once this was applied.
        original = ImageOps.exif_transpose(original)
        original = original.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Deliberately generic: PIL's own exception text can include the server-side
        # temp file path, which must never reach the client. The original exception
        # is still available server-side via `from exc` for anyone logging this.
        raise PramaanImageError(
            "Could not read the uploaded file as an image. It may be corrupted, "
            "empty, or not a supported image format."
        ) from exc

    if original.width < 10 or original.height < 10:
        raise PramaanImageError("Image is too small to be a label photo")

    cv_img = cv2.cvtColor(np.array(original), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)

    enhanced = Image.fromarray(contrasted).convert("RGB")
    return PreprocessedImage(original=original, enhanced=enhanced)
