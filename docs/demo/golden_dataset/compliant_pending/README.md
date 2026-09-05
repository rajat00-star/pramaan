# Golden case: COMPLIANT — BLOCKED, not fabricated

## Status: not yet demonstrated with a real product

This case requires a **real physical product**, photographed by a person and
run through the actual pipeline, that reaches an automatic COMPLIANT verdict
purely from what OCR/extraction can read off the label. The agent producing
this dataset has no camera and no access to physical products, so it cannot
supply this input itself — and fabricating one (e.g. rendering a clean
synthetic label and calling it a "real product") would defeat the entire
point of this exercise, which is to prove the system works on a genuine,
unscripted real-world photo, not on cooperative test input.

**This is reported honestly rather than faked.** See
`backend/tests/test_pipeline_e2e.py::test_compliant_label_end_to_end` for
proof the pipeline *can* reach COMPLIANT end-to-end when given clean input —
that test already passes today, using a rendered (non-photographic) label.
What is missing is a *real camera photo* of a *real commercial product* that
clears the same bar.

## What blocked every one of the 11 real photos tested so far

Across all 11 real product photos in the earlier real-world validation round
(`docs/PraMaan_Real_World_Validation_Report.pdf`), the best result was 1 of 6
applicable fields reaching PASS (the facewash photo); every other photo
reached 0 of 6. The blockers, in order of frequency, were:

1. **Multi-column label layouts** — field labels and values separated across
   columns or lines, which a line-anchored regex extractor cannot safely
   reconstruct once OCR interleaves them (see
   `docs/PraMaan_Real_World_Validation_Report.pdf`, Section 8).
2. **Low source resolution** on downloaded/older photos.
3. **Small print** on nutrition panels and legal boilerplate — exactly the
   text most likely to be missed or garbled.
4. **Curved / reflective packaging surfaces** causing partial OCR legibility.

## What a candidate COMPLIANT photo needs (per the task's own Part 1 criteria)

To give this case a real chance of reaching automatic COMPLIANT, a candidate
photo should have:

- A **single-column** label layout (all seven required fields printed as
  separate, unbroken lines — not split across a two-column price/date table
  like MyFitness, or wrapped ingredient blocks like the facewash photo)
- **High resolution** (a modern phone's default photo resolution is enough;
  avoid pre-compressed/downloaded images)
- **Straight-on framing**, minimal skew or perspective distortion
- **Good, even lighting** with minimal glare — flat matte packaging (a box or
  paper wrapper) will OCR far better than a curved, reflective plastic bottle
- All seven required declarations legible in one photo: manufacturer/packer
  address, common/generic name, net quantity (with a recognised unit — g, kg,
  ml, l, or a count), month+year of manufacture, MRP stating "inclusive of
  all taxes", and consumer-care contact details

Indian packaged snack boxes, soap/detergent cartons, and tea/spice packets
with a single back-panel declaration block (printed, not embossed) are
plausible candidates — this is a suggestion for what to try, not a promise
any specific product will clear every field.

## Attempt log: 2 real products tested, both still REVIEW

Two real products were tested since the section above was written: **Saffola
Masala Oats, Classic Masala with Millets, 38 g** (front + back photos) and
**Monster Mango (Juiced Monster)**, an imported energy drink can. Both
already had far better label conditions than the 11 photos from the earlier
validation round — the Monster Mango can, in particular, produced the best
raw OCR mean confidence of any real photo tested to date (67.1%).

**Neither reached COMPLIANT.** Full per-field diagnosis, including exact OCR
output quoted for every miss, is in `attempts/README.md`. In short:

- **Saffola** (best result so far): `manufacturer_packer_importer` genuinely
  PASSed (84.25% confidence) — the first real product to PASS a field since
  the original 11-photo round. The other 5 applicable fields missed for five
  different, independent reasons (no literal "Product:" keyword on a
  brand-only front panel, a value OCR never recognised at all, two values
  printed in a separately-stamped block with no adjacent keyword, and one
  keyword-bearing line broken by a leading bullet character).
- **Monster Mango**: 0 of 6 applicable fields found despite the best OCR
  quality yet, because this label's own phrasing ("Distributed by", "Imp.
  by", "For Feedback/Complaint") falls outside the current keyword
  vocabulary, plus single-character OCR misreads at two exact anchor points
  ("Froduct", "orlgin"). This attempt also surfaced a genuine, reportable gap:
  the "is this product imported" detection missed this product's own EU
  origin declaration due to one OCR-misread character, so `country_of_origin`
  was (incorrectly) marked NOT_APPLICABLE instead of an unresolved required
  field — logged as a fix candidate for a future session, not patched here.

This raises the bar on what "COMPLIANT-capable" real packaging needs to look
like: even good OCR is not sufficient if the label's own vocabulary and
layout fall outside the keyword-anchored extractor's coverage.

## Attempt 3: Tata Tea Premium — found and fixed a critical false-verdict bug

A third real product, **Tata Tea Premium, 250 g**, was tested — the highest
raw OCR quality of any real photo this project has processed (80.6% mean
confidence). It surfaced a genuine, critical bug: **a real, physically
compliant product was reported NON_COMPLIANT**, because its MRP box prints
"MRP ₹ 170.00" and "(inclusive of all taxes)" as two separate lines, and the
extractor only ever read the first one.

This was fixed the same session it was found (the same standard applied to
the earlier MyFitness defect): `app/pipeline/extraction.py` now folds in an
"(inclusive of all taxes)"-style line when it immediately follows an MRP
line and is the *entire* content of that next line — a general fix, not
specific to this product. Two regression tests were added
(`backend/tests/test_extraction.py`), the full suite was re-run (115 passed,
1 skipped, `ruff check` clean), every other real photo with a found
`retail_sale_price` was re-checked for regressions (only MyFitness — byte
-for-byte unchanged), and the golden NON_COMPLIANT demo case was re-verified
to still correctly FAIL. Full writeup: `attempts/tata_tea_premium/evidence.md`.

**After the fix, this photo reaches REVIEW — genuinely, not COMPLIANT.** One
field (`net_quantity`) is honestly gated to REVIEW on low confidence. Two of
the four PASSing fields (`manufacturer_packer_importer`,
`common_generic_name`) turned out to carry **corrupted evidence text** from
an unrelated, already-known multi-column OCR interleaving defect — they PASS
only because their conclusion happens to be true, not because the system
actually read the right text. This is disclosed in full in the evidence
file rather than presented as a clean win, because a PASS built on wrong
evidence is not something this project is willing to call trustworthy, even
when it would make the overall picture look better.

**Net effect of this attempt:** one real, demo-critical bug found and fixed
(a false accusation against a compliant product, now corrected), and the
COMPLIANT bar confirmed to still require either better real-world layouts
than what commercial FMCG packaging typically offers, or the layout-aware
extraction this project has always named as future work — not another
narrow patch.

## How to complete this case

1. Take 2+ candidate photos meeting the criteria above.
2. Run each through the live API exactly as the other two golden cases were:
   `POST /api/scans` with the photo, using the `citizen_demo` account.
3. If a photo reaches `overall_verdict: "COMPLIANT"`, copy the image into this
   directory (renaming it `photo.jpg`), save the actual API response as
   `actual_api_response.json`, write an `evidence.md` following the same
   structure as the other two golden cases, and add an entry to
   `../golden_demo_manifest.json`.
4. If no candidate reaches COMPLIANT, keep testing — but do not weaken the
   confidence threshold, add a demo-specific bypass, or otherwise alter the
   pipeline to force a result. Report the exact blocking field(s) instead, as
   this README does for the 11 photos already tried.
