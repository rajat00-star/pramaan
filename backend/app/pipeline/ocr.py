"""OCR engine abstraction.

PaddleOCR was the architecture's stated choice, but its model downloads and the
paddlepaddle framework are heavyweight and unverified in this environment.
Tesseract 5 (installed via Homebrew, with the full Indic-language pack) is used
instead: it is a real, independently-verifiable OCR engine — not a mock — and it
natively reports a per-word confidence score, so field-level confidence in this
prototype is measured, never invented. Swapping in PaddleOCR later means adding
a class that implements OCREngine; nothing downstream changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pytesseract
from PIL import Image
from pytesseract import TesseractError, TesseractNotFoundError

from app.pipeline.errors import PramaanOCRError

# Tesseract's default page-segmentation mode (PSM 3, "fully automatic") assumes a
# document-like page and can find literally nothing on a real product photo where
# text sits in scattered blocks against large graphical/branded regions — verified
# directly on real product photos during validation, not a hypothetical. PSM 11
# ("sparse text: find as much text as possible, no particular order") recovers
# text in exactly that situation. It is used ONLY as a fallback when the primary
# pass finds nothing, because on already-working images it was measurably *worse*
# (noisier, more fragmented) than the default — this is a safety net, not a
# universal replacement.
_FALLBACK_PSM = "11"


@dataclass
class Word:
    text: str
    confidence: float  # 0-100 as reported by the OCR engine, or -1 if the engine assigns none
    left: int
    top: int
    width: int
    height: int
    line_id: tuple[int, int, int]  # (block_num, par_num, line_num) — groups words into lines


@dataclass
class OCRResult:
    full_text: str
    words: list[Word]
    # (start_char, end_char) into full_text for the corresponding entry in `words`
    word_spans: list[tuple[int, int]] = field(default_factory=list)
    engine: str = "tesseract"
    lang: str = "eng"
    mean_confidence: float | None = None
    psm_used: str | None = None  # which page-segmentation mode actually produced this result


class OCREngine(ABC):
    @abstractmethod
    def run(self, image: Image.Image) -> OCRResult: ...


class TesseractOCREngine(OCREngine):
    def __init__(self, langs: str = "eng"):
        self.langs = langs

    def _run_pass(self, image: Image.Image, config: str = "") -> OCRResult:
        try:
            data = pytesseract.image_to_data(
                image, lang=self.langs, output_type=pytesseract.Output.DICT, config=config
            )
        except TesseractNotFoundError as exc:
            raise PramaanOCRError(
                "Tesseract binary not found on PATH. Install it (e.g. `brew install "
                "tesseract tesseract-lang`) and ensure it is on PATH."
            ) from exc
        except TesseractError as exc:
            # Generic on purpose: Tesseract's own error text can reference the
            # server-side temp file path. Original exception stays available
            # server-side via `from exc` for logging.
            raise PramaanOCRError("OCR engine failed while processing this image.") from exc

        words: list[Word] = []
        full_text = ""
        spans: list[tuple[int, int]] = []
        prev_line_id: tuple[int, int, int] | None = None

        n = len(data.get("text", []))
        for i in range(n):
            text = data["text"][i].strip()
            if not text:
                continue
            conf_raw = data["conf"][i]
            try:
                confidence = float(conf_raw)
            except (TypeError, ValueError):
                confidence = -1.0

            line_id = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            if prev_line_id is not None and line_id != prev_line_id:
                full_text += "\n"
            elif prev_line_id is not None:
                full_text += " "
            prev_line_id = line_id

            start = len(full_text)
            full_text += text
            end = len(full_text)
            spans.append((start, end))

            words.append(
                Word(
                    text=text,
                    confidence=confidence,
                    left=int(data["left"][i]),
                    top=int(data["top"][i]),
                    width=int(data["width"][i]),
                    height=int(data["height"][i]),
                    line_id=line_id,
                )
            )

        confidences = [w.confidence for w in words if w.confidence >= 0]
        mean_confidence = sum(confidences) / len(confidences) if confidences else None

        return OCRResult(
            full_text=full_text,
            words=words,
            word_spans=spans,
            engine="tesseract",
            lang=self.langs,
            mean_confidence=mean_confidence,
            psm_used=config or "default",
        )

    def run(self, image: Image.Image) -> OCRResult:
        result = self._run_pass(image)
        if not result.full_text.strip():
            result = self._run_pass(image, config=f"--psm {_FALLBACK_PSM}")
        return result
