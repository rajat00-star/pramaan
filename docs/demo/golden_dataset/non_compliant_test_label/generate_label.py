"""Renders the golden NON_COMPLIANT demo label (label.png in this directory).

This is a controlled TEST/DEMO label, not a real commercial product — a real
product must never be misrepresented as non-compliant. The label is printed
text (clean, single column, high contrast) so OCR/extraction confidence is
high and the resulting NON_COMPLIANT verdict comes from a genuine rule
violation, not from OCR noise.

The single deliberate violation: the MRP line omits "inclusive of all taxes",
which is a real and common Legal Metrology violation (Rule 6(1)(e)) — not an
invented rule. Every other field is filled in correctly so the demo shows
exactly one FAIL against six otherwise-clean fields, isolating the violation.

Run from anywhere with the backend venv active:
    python3 docs/demo/golden_dataset/non_compliant_test_label/generate_label.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).parent

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_BOLD_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default(size=size)


LABEL_LINES = [
    "Manufactured by: PraMaan Test Labs Pvt Ltd, 7 Residency Road, Bengaluru 560025",
    "Product: Herbal Bathing Soap (Test Sample)",
    "Net Wt: 125 g",
    "Mfg Date: 02/2026",
    "MRP Rs. 45.00",
    "Customer Care: 1800-000-1111, care@pramaan-test.example.com",
]

WIDTH, HEIGHT = 1600, 1050


def build():
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    banner_font = _font(_BOLD_FONT_CANDIDATES, 34)
    banner = "*** TEST / DEMO LABEL --- NOT AN ACTUAL COMMERCIAL PRODUCT ***"
    draw.rectangle([(0, 0), (WIDTH, 70)], fill=(178, 34, 34))
    draw.text((30, 18), banner, fill="white", font=banner_font)

    body_font = _font(_FONT_CANDIDATES, 32)
    y = 140
    for line in LABEL_LINES:
        draw.text((60, y), line, fill="black", font=body_font)
        y += 90

    footer_font = _font(_FONT_CANDIDATES, 22)
    draw.text(
        (60, HEIGHT - 60),
        "Golden demo artifact -- created for SIH 2026 PraMaan demonstration. Not a real product.",
        fill=(120, 120, 120),
        font=footer_font,
    )

    out_path = OUT_DIR / "label.png"
    img.save(out_path)
    print("wrote", out_path, img.size)


if __name__ == "__main__":
    build()
