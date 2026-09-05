# Attempt 3: Tata Tea Premium, 250 g — found and fixed a critical false-verdict bug

Real camera photo (`photo.png`, user-confirmed to be a genuine photo of a
physical box despite an AI-tool-style filename inherited from an
intermediate save step) of the back panel of a Tata Tea Premium carton.

This attempt did not reach COMPLIANT, but it found — and this session fixed
— a **critical false NON_COMPLIANT bug** affecting a real, genuinely
compliant product. That is reported in full below, in the same spirit as the
MyFitness defect in `docs/PraMaan_Real_World_Validation_Report.pdf` Section 5.

## Before the fix: false NON_COMPLIANT

Scan `a97bfced95f9455786f7e6a3b9816d72` was first evaluated before this
fix existed. OCR mean confidence was **80.6%** — the highest of any real
product photo tested this session — and the result was:

**Overall verdict: NON_COMPLIANT** (`actual_api_response_before_fix.json`)

The label's MRP box genuinely reads:

```
MRP ₹ 170.00
(inclusive of all taxes)
```

...as two separate physical lines. OCR reproduced this faithfully:
`"MRP 2% 170.00\n(inclusive of all taxes)"` (the ₹ symbol was misread as
"2%" — a separate, harmless OCR error). The extractor's line-anchored
capture (`_LINE_VALUE = r"([^\n]+)"` in `app/pipeline/extraction.py`) only
ever captured the first line, `"2% 170.00"`. `_evaluate_retail_sale_price`
then correctly-by-its-own-logic-but-wrongly-in-fact checked for `"incl"` in
that captured text, found nothing, and returned **FAIL**: *"MRP is declared
as '2% 170.00' but does not state it is inclusive of all taxes."*

**This was a false accusation.** The physical package unambiguously states
the price is inclusive of all taxes — one line below where the extractor
stopped looking. A real, compliant product was reported NON_COMPLIANT.

## The fix

Added `_INCLUSIVE_TAXES_CONTINUATION_RE` and
`_retail_price_continuation_span()` to `app/pipeline/extraction.py`: when the
captured MRP line does not itself contain "incl", the extractor now checks
whether the immediately following line is *wholly* an "(inclusive of all
taxes)"-style clause (nothing else on that line — deliberately narrow, so an
unrelated nearby line is never absorbed) and, if so, folds it into the same
declaration. This is a general fix, not specific to this product or photo —
two-line MRP declarations (amount on one line, the tax clause wrapped to the
next) are a common real Indian packaging convention, not unique to Tata Tea.

Regression tests added to `backend/tests/test_extraction.py`:
- `test_retail_sale_price_folds_in_inclusive_of_taxes_clause_from_next_line`
- `test_retail_sale_price_does_not_fold_in_an_unrelated_next_line` (guards
  against over-absorbing unrelated text)

Full suite after the fix: **115 passed, 1 skipped** (113 + 2 new),
`ruff check` clean. Regression-checked against every other real photo with a
found `retail_sale_price` value (only MyFitness, at 19% confidence, gated to
REVIEW before this code path is ever reached) — confirmed byte-for-byte
unchanged (`/tmp/myfitness_recheck.json` at time of writing). Also confirmed
the golden NON_COMPLIANT demo case (`non_compliant_test_label`, which
deliberately has no continuation line) still correctly FAILs —
`test_golden_non_compliant_case_remains_non_compliant` still passes.

## After the fix: same photo, re-run against the live API

Scan `a97bfced95f9455786f7e6a3b9816d72` re-run after restarting the server
with the fix applied (`actual_api_response_after_fix.json`):

| Field | Status | Raw value | Confidence |
|---|---|---|---|
| manufacturer_packer_importer | PASS | `"strong odours."` | 96.0% |
| country_of_origin | NOT_APPLICABLE | — | — |
| common_generic_name | PASS | `"Tea [e\| ional Information"` | 87.0% |
| net_quantity | REVIEW | `"250g EeraT kcal a"` | 36.0% (below 60% threshold) |
| date_of_manufacture | PASS | `"15/JAN/2025"` | 75.0% |
| **retail_sale_price** | **PASS** | `"2% 170.00 (inclusive of all taxes)"` | 84.3% |
| consumer_care_details | PASS | `"Executive,"` | 96.0% |

**Overall verdict: REVIEW** (was NON_COMPLIANT). Replay confirms
reproducibility (`replay.json`, `"reproduced": true`).

## Why this is still not COMPLIANT — and why two of the PASSes above should not be fully trusted either

`net_quantity` correctly sits in REVIEW: its 36% confidence is below the 60%
gate, so the system safely declined to guess.

But look closely at the raw values for `manufacturer_packer_importer`
(`"strong odours."`), `common_generic_name`
(`"Tea [e| ional Information"`), and `net_quantity`
(`"250g EeraT kcal a"`) — **none of these are what the physical label
actually says at that point.** The real cause: this label has a two-column
layout at that vertical position (a white info box on the left, a
"Nutritional Information" table on the right), and Tesseract's line grouping
interleaved text across both columns on the same row:

```
Lic. No. 1014071000859 [fssai]    Store in a cool, dry place away from:
Marketed by:                       strong odours.
Tata Consumer Products Limited,
```

The keyword "Marketed by:" (left column) and "strong odours." (the tail end
of the right column's storage instructions, on the same OCR row) got
concatenated into one line, and the line-anchored capture picked that up as
if "strong odours." were the declared manufacturer. The same interleaving
corrupted `common_generic_name` (merging "Tea" with a fragment of
"Nutritional Information") and `net_quantity` (merging "250g" with "Energy
(kcal)" misread as "EeraT kcal").

**`manufacturer_packer_importer` and `common_generic_name` PASS here, but
only because the compliance conclusion happens to be true anyway (the
product's name and manufacturer genuinely are declared) — not because the
system correctly read the label.** The stored evidence text for those two
fields is wrong and would mislead a human reviewer who trusted it without
checking the source photo. This is a real, disclosed limitation of the
line-based extractor on multi-column layouts (the same root cause already
documented in `docs/PraMaan_Real_World_Validation_Report.pdf` Section 8),
not a new class of bug — but this is the first time it has been caught
producing a PASS on a real photo rather than a REVIEW, and it deserves being
named plainly rather than glossed over because the demo-desired outcome
(reaching further toward COMPLIANT) benefited from it this time.

No further fix was attempted for this column-interleaving root cause — doing
so safely requires layout-aware extraction (already named as future work),
not another narrow regex, which would risk over-fitting to this exact photo.

## Is this genuinely sufficient for COMPLIANT?

**No.** One field is honestly gated to REVIEW (net_quantity, low
confidence), and two of the four PASSing fields carry evidence text that is
demonstrably wrong even though their conclusions happen to be correct. A
verdict built on wrong evidence is not something this project is willing to
call genuinely COMPLIANT, even when REVIEW would already have quietly
resolved to a passing-looking state. The honest verdict is REVIEW, and that
is what the system reports.
