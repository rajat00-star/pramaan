"""Label-region detection.

The target architecture (per the PraMaan deck) uses YOLOv8 to localise the label
region within a wider product photo. No trained detector or annotated dataset
exists yet for this hackathon prototype, so this module defines the interface
every detector must satisfy and ships one honest fallback: treat the whole
photo as the label region. Swapping in a real YOLOv8Detector later means
implementing LabelDetector and changing one line in pipeline.py — nothing
downstream (OCR, extraction, rule engine) needs to change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image


@dataclass
class LabelRegion:
    image: Image.Image
    bbox: dict  # {left, top, width, height} in pixels of the source image
    detector_confidence: float | None  # None when the detector does not estimate one
    method: str


class LabelDetector(ABC):
    @abstractmethod
    def detect(self, image: Image.Image) -> list[LabelRegion]:
        """Return one or more candidate label regions, most likely first."""


class FullImageDetector(LabelDetector):
    """MVP fallback: assume the whole photo is the label (citizen crops it before upload)."""

    method = "full_image_fallback"

    def detect(self, image: Image.Image) -> list[LabelRegion]:
        width, height = image.size
        region = LabelRegion(
            image=image,
            bbox={"left": 0, "top": 0, "width": width, "height": height},
            detector_confidence=None,
            method=self.method,
        )
        return [region]


class YOLOv8LabelDetector(LabelDetector):
    """Placeholder for the production detector described in the architecture.

    Not implemented: no trained weights or annotated label dataset exist yet.
    Left here so the interface it must satisfy (LabelDetector.detect) is explicit
    and reviewable ahead of the actual training work.
    """

    def __init__(self, weights_path: str):
        self.weights_path = weights_path

    def detect(self, image: Image.Image) -> list[LabelRegion]:
        raise NotImplementedError(
            "YOLOv8LabelDetector requires trained weights and an annotated label "
            "dataset, neither of which exist yet. Use FullImageDetector for now."
        )
