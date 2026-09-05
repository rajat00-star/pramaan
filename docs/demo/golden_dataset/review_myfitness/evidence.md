# Golden case: REVIEW → human correction → final deterministic evaluation

## What this is

A real camera photo (`photo.jpg`) of a real product — MyFitness Peanut Butter,
510 g, back label — taken during the earlier real-world validation pass on
this project. It is reused here rather than re-photographed because it is
already the project's best-documented example of the REVIEW workflow: this
exact photo previously exposed and then confirmed the fix for a critical
defect (a punctuation-only OCR capture that produced a false NON_COMPLIANT
verdict — see `docs/PraMaan_Real_World_Validation_Report.pdf`, Section 5, and
`backend/tests/test_extraction.py::test_net_quantity_does_not_report_found_for_punctuation_only_value`).

## Step 1 — real photo, real OCR uncertainty

Posted to the live API (`actual_api_response.json`). The photo is a
hand-held, close-up shot of a curved plastic container with small print;
OCR mean confidence was low and only one field (`retail_sale_price`, at
19.0% confidence) was extracted at all.

| Field | Status | Reason |
|---|---|---|
| manufacturer_packer_importer | REVIEW | Not detected by OCR/extraction |
| country_of_origin | NOT_APPLICABLE | Not an imported product |
| common_generic_name | REVIEW | Not detected by OCR/extraction |
| net_quantity | REVIEW | Not detected by OCR/extraction |
| date_of_manufacture | REVIEW | Not detected by OCR/extraction |
| retail_sale_price | REVIEW | Found, but confidence (19.0%) below the 60.0% review threshold |
| consumer_care_details | REVIEW | Not detected by OCR/extraction |

**Overall verdict: REVIEW.** No field reached a confident PASS or FAIL, so the
system correctly refused to guess.

## Step 2 — human correction against the physical package

Zooming into the same photo, five of the six applicable fields are legible on
the physical container and were corrected by an inspector account
(`inspector_demo`) via `POST /api/scans/{id}/review`, one field at a time —
see `actual_api_response_after_correction.json` for the resulting scan state
and `audit_trail.json` for the full event log (`SCAN_CREATED`,
`RULES_EVALUATED`, `SCAN_COMPLETED`, then five `FIELD_CORRECTED` events, one
per correction below).

| Field | Corrected value | Read from |
|---|---|---|
| manufacturer_packer_importer | Tanvi Fitness Private Limited, InnoHouse, 2nd Floor, Plot No. 1, 4 Bay, Sector 32, Gurugram, Haryana 122001 (FSSAI Lic. No. 10824999000152) | "Marketed by" block, back label |
| net_quantity | 510 g | "Net Qty." line, back label |
| date_of_manufacture | 03.08.2026 | "MFD." line, back label |
| retail_sale_price | Rs. 319.00 (Inclusive of all taxes) | "MRP/USP ₹" line, back label |
| consumer_care_details | care@myfitness.co.in, +91 7096699111 | Vertical text, left edge of back label |

Each correction is stored with `reviewer_user_id`, `previous_verdict`, the
original (uncorrected) OCR value, and a note explaining it was manually
verified against the physical container — never a client-supplied claim of
who made the change.

## Step 3 — final deterministic evaluation

After all five corrections, the rule engine re-evaluated each corrected field
deterministically (same `evaluate_field` code path as every other scan — see
`app/routes/review.py`):

| Field | Status | Reason |
|---|---|---|
| manufacturer_packer_importer | **PASS** | Declared |
| country_of_origin | NOT_APPLICABLE | Not an imported product |
| common_generic_name | **REVIEW (unchanged)** | Still not detected — see below |
| net_quantity | **PASS** | `510 g` — recognised unit |
| date_of_manufacture | **PASS** | Declared |
| retail_sale_price | **PASS** | States inclusive of all taxes |
| consumer_care_details | **PASS** | Declared |

**Final verdict: REVIEW** (not COMPLIANT) — deliberately left this way.

## Why the final verdict is still REVIEW, not COMPLIANT

`common_generic_name` ("Peanut Butter") was **not corrected**, because it is
not legible on this photograph — this photo shows only the back label; the
product's generic name appears on the front of the container, which was not
captured. Inventing that value from context (the product's known brand name)
would be exactly the kind of fabrication the underlying validation work
explicitly prohibited. Leaving one field genuinely unresolved after
correcting the other five is the honest outcome, and demonstrates that the
review workflow corrects only what a human can actually verify from the
evidence in front of them — it does not silently manufacture completeness.

## Reproducibility

`replay.json` (fetched via `GET /api/scans/{id}/replay`) confirms this scan's
per-field results are reproducible against the same rule-pack version and
content hash it was originally evaluated with.
