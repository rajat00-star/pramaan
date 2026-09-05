# PraMaan Golden Demo Dataset — Report

This report documents three golden demo cases meant to prove PraMaan's three
intended outcomes (COMPLIANT, NON_COMPLIANT, REVIEW) each through a genuine,
reproducible run of the real pipeline — not through fabricated or
hand-adjusted results. Full evidence lives in `docs/demo/golden_dataset/`.

**Honest headline: two of three states are demonstrated. COMPLIANT is not —
see Section 2.**

Rule pack in force for every case below: version `1`, SHA-256
`f7be6482b898559dd2f00f3dd4247a548ab2434c37f5618c1a905994bd6c2be3`.

## 1. Summary table

| Case | Input | Expected | Actual | Evidence | Rule | Result |
|---|---|---|---|---|---|---|
| COMPLIANT | *(none — no real product tested has cleared all applicable fields)* | COMPLIANT | — | `compliant_pending/README.md` | — | **BLOCKED** — honestly unresolved, not faked |
| NON_COMPLIANT | `non_compliant_test_label/label.png` — controlled TEST/DEMO label | NON_COMPLIANT | NON_COMPLIANT | `non_compliant_test_label/actual_api_response.json`, `replay.json` | Rule 6(1)(e) — MRP must state "inclusive of all taxes" | **PASS** — genuine, reproducible |
| REVIEW | `review_myfitness/photo.jpg` — real photo, MyFitness Peanut Butter 510 g | REVIEW | REVIEW (before and after 5-field human correction) | `review_myfitness/actual_api_response.json`, `actual_api_response_after_correction.json`, `audit_trail.json`, `replay.json` | Rule 6(1)(a)/(b)/(c)/(d)/(e)/(2) — multiple fields | **PASS** — genuine, reproducible |

## 2. COMPLIANT — why it is not demonstrated, in full

The task that produced this dataset was explicit: COMPLIANT must come from a
real, physically-verifiable product photo — not a rendered or synthetic
label. No camera or physical product access was available to generate new
candidate photos in this session.

Of the 11 real product photos already collected in the project's earlier
real-world validation round, none reached COMPLIANT. The best result (the
face-wash photo) reached 1 of 6 applicable required fields; every other photo
reached 0 of 6. The dominant blockers, most-to-least frequent: multi-column
label layouts that a line-based extractor cannot safely reconstruct, low
source resolution, small print on nutrition/legal panels, and curved
reflective packaging surfaces. Full detail and the exact criteria a
COMPLIANT-candidate photo would need to meet are in
`docs/demo/golden_dataset/compliant_pending/README.md`.

Separately, `backend/tests/test_pipeline_e2e.py::test_compliant_label_end_to_end`
already proves the pipeline mechanism *can* reach COMPLIANT given clean
input — it does today, and passes as part of the 113-test suite. What remains
missing is a real photograph, not a code capability.

## 3. NON_COMPLIANT — how the demo works

`non_compliant_test_label/label.png` is a clearly-marked TEST/DEMO label
(red banner top and bottom, explicit "NOT AN ACTUAL COMMERCIAL PRODUCT"
text) — never a real product misrepresented as non-compliant. It states an
MRP of "Rs. 45.00" with no statement that this is inclusive of all taxes,
which genuinely violates Rule 6(1)(e) of the Legal Metrology (Packaged
Commodities) Rules, 2011 — a real and common violation, not an invented one.

Run through the live API: 6 of 7 fields PASS or are NOT_APPLICABLE;
`retail_sale_price` FAILs on exactly the stated reason. Aggregation
(`aggregate_verdict_from_statuses`) returns NON_COMPLIANT because any FAIL
dominates, regardless of how many fields PASS. Replaying the scan against the
live rule pack reproduces the identical verdict (`replay.json`,
`"reproduced": true`).

## 4. REVIEW — how the demo works, including human correction

`review_myfitness/photo.jpg` is a real, previously-taken camera photo of a
real product (MyFitness Peanut Butter, 510 g back label). Posted to the live
API, OCR mean confidence was low and only one field was extracted at all
(`retail_sale_price`, 19.0% confidence — below the 60.0% review threshold),
so the initial verdict is REVIEW with 6 of 7 applicable fields unresolved.

Zooming into the same photo, five of those six fields are legible on the
physical package and were corrected by an inspector account, one at a time,
via `POST /api/scans/{id}/review`. Each correction is independently
re-evaluated by the same deterministic rule engine and recorded in the audit
trail (`SCAN_CREATED`, `RULES_EVALUATED`, `SCAN_COMPLETED`, then five
`FIELD_CORRECTED` events).

The **sixth** field, `common_generic_name` ("Peanut Butter"), is deliberately
left uncorrected — it is not legible on this photo, which shows only the back
label. The final verdict stays REVIEW, not COMPLIANT, because that field is
genuinely still unresolved. This is the honest outcome, not an oversight: the
review workflow corrects only what a human can actually verify from the
evidence in front of them.

## 5. Regression protection

`backend/tests/test_golden_demo_dataset.py` adds 7 tests (6 executed, 1
intentionally skipped with a named reason) to the suite:

- The golden NON_COMPLIANT case stays NON_COMPLIANT, with the violation
  isolated to `retail_sale_price`.
- The golden REVIEW case stays REVIEW, and specifically that `net_quantity`
  is never reported as "found" for this photo (the exact defect this photo
  previously exposed).
- Both golden scans record the live rule-pack version and SHA-256 hash, and
  can be replayed reproducibly.
- The full human-correction workflow reaches the correct final per-field
  statuses and the correct overall verdict.
- No production source file (`app/pipeline/*.py`, `app/routes/*.py`,
  `app/models.py`, `app/auth.py`) contains any hardcoded reference to this
  dataset's ids, filenames, or product names — i.e., no demo-specific bypass
  exists anywhere the rule engine or pipeline could reach.
- The COMPLIANT case has an explicit `pytest.mark.skip` placeholder so its
  absence shows up in test output rather than being silently missing.

Full suite result at the time of writing: **113 passed, 1 skipped** (107
pre-existing + 6 new), `ruff check` clean.

## 6. Recommended 3–5 minute SIH demo script

1. **COMPLIANT (via existing test, not a live scan)** — Rather than attempt an
   unrehearsed live COMPLIANT photo (none has been demonstrated — see Section
   2), state this directly to the judges: show
   `test_pipeline_e2e.py::test_compliant_label_end_to_end` passing in the test
   suite as proof the mechanism works, and be upfront that no real-world photo
   has cleared it yet. This is a stronger position than an unrehearsed
   COMPLIANT attempt that might fail live.
2. **NON_COMPLIANT** — Upload `non_compliant_test_label/label.png` live. Walk
   through the response: point at the MRP line missing "inclusive of all
   taxes," show the FAIL status and its exact clause citation (Rule 6(1)(e)),
   and show every other field PASSing — a clean, isolated violation.
3. **REVIEW + Human Correction** — Upload `review_myfitness/photo.jpg` live.
   Show the initial REVIEW verdict with most fields unresolved. Switch to the
   inspector account and correct 2–3 fields live (net_quantity, MRP) by
   reading them off a zoomed photo. Show the verdict recompute. Then make the
   key point explicitly: `common_generic_name` stays unresolved because it
   genuinely isn't visible on this photo — the system does not fabricate
   completeness.
4. **Historical rule replay** — Call `GET /api/scans/{id}/replay` on the
   NON_COMPLIANT scan from step 2. Show `reproduced: true` and the exact
   rule-pack SHA-256 hash — the verdict can be regenerated from its logged
   inputs at any later date, even after the active rule pack changes.
5. **Audit trail** — Show `GET /api/scans/{id}/audit` on the REVIEW scan from
   step 3: `SCAN_CREATED` → `RULES_EVALUATED` → `SCAN_COMPLETED` → five
   `FIELD_CORRECTED` events, each with the reviewer identity, timestamp,
   original OCR value, and corrected value — an append-only record of exactly
   who changed what and when.

**Lead with the honesty, not the polish.** The strongest line in this demo is
not "watch it work" — it's "watch it refuse to guess, and watch exactly how a
human closes that gap when the evidence allows it, and admits when it can't."
