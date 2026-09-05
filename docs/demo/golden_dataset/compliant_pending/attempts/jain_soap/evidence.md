# Attempt 4: Jain Soap (toilet soap, marketed by Marico) — excellent label, unusable image resolution

Photo of the back declaration panel of a Jain Soap bar, marketed by Marico
Ltd. Read-only pass: no production code was touched before or during this
run, and the result below is the unmodified, single-shot output of
`POST /api/scans` (scan `6953891c3ab5494490f1f9368c55421b`).

## What the physical label actually declares (visually verified)

This is, by a wide margin, the cleanest, most complete single-panel
declaration seen in this dataset so far — every one of the 6 applicable
fields is present, in a single column, in plain print:

- **Manufacturer/packer:** "Mfd & Pkd by: Jain Soap, 39/A, Devam Estate,
  Opp. Gayatri Petrol Pump, Santej, Ta. Kalol, Gandhinagar (Guj) 382721.
  Mfg. Lic. No.: COS/GC/1135" and "Mktd By: Marico Ltd., 175 CST Road,
  Kalina, Santacruz East, Mumbai-400098, Maharashtra."
- **Common/generic name:** "MADE IN INDIA TOILET SOAP, Grade 1.76% TFM"
- **Net quantity:** "Net Qty (when packed): 75 g X 2 Units = 150 g"
- **Date of manufacture:** "Mfg. Date: 03/2025"
- **Retail sale price:** "MRP ₹ (inclusive of all taxes): 289.00"
- **Consumer care:** "For Feedback, Contact: Marico Consumer Services Cell,
  PO Box No. 9411, Mumbai 400093... Call: 1800222248, Email: csc@marico.com"

If this exact layout had been captured at a usable resolution, it would be
the strongest COMPLIANT candidate tested in this entire dataset.

## What the pipeline actually produced

- **OCR mean confidence: 20.6%** — the lowest of any real image tested.
- Raw OCR output is almost total noise:
  `"Balas oy 8, Mahesh.\nEEE eerie\nSean ein\n..."` — no field is
  recoverable as readable text at all.
- **0 of 7 fields found.** Every applicable field: REVIEW ("not detected by
  OCR/extraction"). `country_of_origin`: NOT_APPLICABLE (correct — not an
  imported product).
- **Overall verdict: REVIEW.**
- Replay confirms reproducibility (`replay.json`, `"reproduced": true`)
  against rule pack v1, hash `f7be6482b898559d...`.

## Root cause: this is an image-resolution problem, not a code defect

Measured directly: `photo.png` is **500×500 pixels at 72 DPI**. Every real
phone-camera photo processed successfully in this dataset has been
2000px+ on its short edge (typically 3000-5700px); this file is roughly
6-10x smaller on each axis than any other real photo tested. At 500×500,
the six-to-seven lines of small printed declaration text occupy only a
handful of pixels per character — well below what any OCR engine, Tesseract
included, can reliably resolve into readable glyphs. This is the same
"low source resolution" failure class already documented for the four
downloaded product-listing photos in the original 11-photo validation round
(420–651px on the short edge) — this image is smaller still.

**No fix was attempted.** There is no minimal, generalizable code change
that recovers text detail that was never captured in the source pixels —
that would require image super-resolution (a major new capability, not a
narrow fix) with no guarantee of recovering genuinely lost information, and
risks fabricating text that merely looks plausible. Per the standing rule
for this dataset (never force a result, never patch around a hard input
-quality limit), this is reported as a disclosed limitation, not patched.

## Verdict on this attempt

**Not COMPLIANT — and not because of any extraction, keyword, layout, or
confidence-gating defect.** This is the one failure class in the entire
attempt history that is purely an input-quality problem: **if this exact
same label is re-photographed at native phone-camera resolution, it is
the single most promising candidate seen so far for a genuine real-product
COMPLIANT verdict** — every required field is present, in one column, in
plain print, with no multi-panel splitting and no marketing-only faces.
