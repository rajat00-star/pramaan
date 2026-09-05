# COMPLIANT attempt log

Every attempt below is a real product, photographed by a person, run through
the actual live PraMaan API (`POST /api/scans`, `citizen_demo` account) with
no code changes, threshold changes, or special-casing of any kind. None
reached COMPLIANT. This file documents exactly why, per field, so the gap is
traceable rather than hand-waved.

Rule pack for every attempt: version `1`, hash
`f7be6482b898559dd2f00f3dd4247a548ab2434c37f5618c1a905994bd6c2be3`.

---

## Attempt 1: Saffola Masala Oats, Classic Masala with Millets, 38 g

Two real photos of the same physical pouch: `front.jpg` (branding side) and
`back.jpg` (ingredients/nutrition side). **PraMaan's architecture accepts one
image per scan** — there is no multi-image fusion — so each was run as an
independent scan. This is itself a disclosed limitation: even if the two
photos together contain every required declaration, the system cannot
currently combine them into a single verdict.

### front.jpg — `actual_api_response_front.json` (scan `a47c8a54025c472d8dcc5e15c091ce35`)

- OCR mean confidence: **31.1%**
- Fields found: **none**
- Verdict: **REVIEW**

**Diagnosis:** the front panel is almost entirely stylized brand artwork (a
glossy heart-shaped logo, decorative script, a photographed bowl of oats) —
there is very little printed body text at all, and what exists is small and
low-contrast against the orange/yellow background. Raw OCR output is mostly
unrecognizable noise (`"Hy 1 May Hh) HW WH, "fi ai iii ail"`). This is not a
keyword-matching problem — OCR itself could not read the panel.

### back.jpg — `actual_api_response_back.json` (scan `62f02af63b3447a08222c36e116b5800`)

- OCR mean confidence: **64.5%**
- Fields found: `manufacturer_packer_importer` = "Marico Ltd. 7th Floor" (confidence 84.25%) → **PASS**
- Verdict: **REVIEW** (6 of 7 applicable fields unresolved)

**Diagnosis, field by field, comparing OCR output against the physical
package (visually verified from the submitted photo):**

| Field | Physically present? | Found by OCR/extraction? | Why not |
|---|---|---|---|
| manufacturer_packer_importer | Yes ("Marketed by: Marico Ltd...") | **Yes — PASS** | — |
| common_generic_name | No literal "Product:"/"Commodity:" line — only graphic branding ("Saffola masala oats", "Classic Masala") | No | The extractor is a keyword-anchored parser (`app/pipeline/extraction.py`); it only recognises `Product`/`Commodity`/`Contents` as a line-starting keyword. This package never states its generic name that way — it relies entirely on brand typography, which no OCR-based keyword match can substitute for without inventing a value. |
| net_quantity | Yes ("Net Qty.: 38 g", printed in the dense bottom-left info block) | No | Tesseract did not recognise this text at all — searched the full raw OCR output for "net" (case-insensitive) and found zero matches. A pure OCR recognition failure on small, densely-packed print, not an extraction-logic issue. |
| date_of_manufacture | Yes (inkjet-stamped "09 AUG 2026" / "09 AUG 2027" just below the barcode) | No | The static printed label text says only "...Lot No., MFD., Use by: refer below" — OCR read "MFD." as "ITD." (a genuine character-level misread), and the actual stamped dates sit in a separate print pass (inkjet over pre-printed plastic) with no adjacent keyword on the same line at all. The line-anchored keyword match has nothing to anchor to here even when OCR is otherwise readable. |
| retail_sale_price | Yes ("₹20.00" in the same inkjet-stamped block) | No | The one on-package mention of "MRP" is in a bulleted disclaimer line ("* MRP ₹ (incl. of all taxes), USP, Lot No., ... refer below") that starts with an asterisk bullet, not the word "MRP" itself — the line-start anchor (added specifically to prevent false-positive mid-sentence matches, see `extraction.py`'s own comment) correctly does not match here. The actual price value is, again, in the separately-stamped block with no adjacent keyword. |
| consumer_care_details | Yes ("For feedback, contact: Marico Consumer Services Cell... 1800222248... csc@marico.com") | No | OCR itself garbled the opening of this exact line to `"yk ) Consume! Services Cell,"` — the "For feedback, contact: Marico" portion was lost entirely, not just misspelled. Even if it had survived intact, "For feedback, contact:" is not one of the recognised keywords ("Customer Care", "Consumer Care", "For complaints") — a second, independent reason this field could not be found here. |
| country_of_origin | N/A (domestic product) | NOT_APPLICABLE | Correct — this is not an imported product. |

**Conclusion for this product:** even combining both photos manually (as a
human inspector would), the extractor's exact-keyword-anchored design misses
4 of 6 applicable fields for reasons that are almost all genuinely different
from each other (missing keyword phrasing entirely, OCR character misreads,
values split across separate print passes with no adjacent label, and a
punctuation-prefixed line breaking the anchor) — this is a realistic sample
of why real FMCG packaging defeats a keyword-only extractor, not a single
fixable bug.

---

## Attempt 2: Monster Mango (Juiced Monster), imported energy drink

One real photo (`photo.jpg`) of the can's back/side label.

- Scan: `9b604609b2eb438bbbe23b04a716e961`
- OCR mean confidence: **67.1%** (the best of the three attempts — most of
  the label text is genuinely, clearly recognised, e.g. "Froduct Name :
  Monster Mango", "Country of orlgin :EU", "NOV 2025")
- Fields found: **none**
- Verdict: **REVIEW**

**Diagnosis, field by field:**

| Field | Physically present? | Found by OCR/extraction? | Why not |
|---|---|---|---|
| manufacturer_packer_importer | Yes ("Mktd. & Distributed by: Snackstar... Imp. by: Tih-Om International...") | No | The label uses "Distributed by" and "Imp. by" — neither is in the recognised keyword list (`Manufactured by / Mfd. by / Packed by / Marketed by / Manufacturer`). This is a real, legitimate phrasing this product uses that the current keyword set does not cover. |
| common_generic_name | Yes ("Froduct Name : Monster Mango" — OCR's own misread of "Product") | No | OCR misread the leading "P" as "F" ("Froduct"), which no longer matches the `Product` keyword. A single-character OCR error at the exact anchor position defeats an exact-string match. |
| net_quantity | The label itself states **"Net Pack : see on Pack"** — the actual net quantity is declared elsewhere (the can's front), not on this photographed side | No | Not a bug: this specific photo genuinely does not carry the net-quantity declaration. Even a human reading only this photo could not determine it. |
| date_of_manufacture | Only "Mfg Month ... NOV 2025" style relative labelling, not printed as "Mfg. Date:" | No | Present but phrased as "Best Before... Month of Import... Mfg Month" — the literal keyword "Mfg. Date" is not present in this format. |
| retail_sale_price | Present but heavily garbled by OCR ("...G1 nel Of All Taxes)" for what should be "...MRP ... (incl. of all taxes)") | No | The OCR output for this line is too corrupted to contain a recognisable "MRP" keyword at all. |
| consumer_care_details | Yes ("For Feedback/Complaint... at snackstar.in@gmail.com... customer care no. +91-11-41645145") | No | Present in OCR output but not preceded by a recognised keyword on its own line ("For Feedback/Complaint" is not in the keyword list, which expects "Customer Care"/"Consumer Care"/"For complaints"). |
| country_of_origin | Yes, and this product **is** genuinely imported ("Imp. by: Tih-Om International", "Country of orlgin :EU") | **NOT_APPLICABLE (incorrectly)** | This is the most notable finding of this attempt. `IMPORTED_SIGNAL_RE` in `extraction.py` requires the literal substring "country of origin" (or "imported by", "made in", or the Hindi equivalent) to detect that Rule 6(1)(aa) applies at all. OCR read the label's actual text as "Country of **orlgin**" (an `i`→`l` misread) — one character off from matching. As a direct result, the system did not even recognise this as an imported product, so it evaluated `country_of_origin` as NOT_APPLICABLE rather than correctly flagging it as an unresolved required field. **This is a genuine gap worth fixing in a future session** (e.g. also matching "Imp. by" — which the label does state clearly and unambiguously, independent of the OCR typo) — it is reported here rather than patched, since this task's scope was to run real images and diagnose, not to modify extraction logic. |

**Conclusion for this product:** the underlying OCR quality was good (67.1%,
the best of the three), but every single field still missed — either because
this label's own phrasing genuinely falls outside the current keyword
vocabulary ("Distributed by", "Imp. by", "For Feedback/Complaint"), or
because of single-character OCR misreads at the exact anchor point
("Froduct", "orlgin"). This is different in kind from the Saffola failures
(mostly OCR/layout) — Monster Mango shows that even good OCR does not help
when a real product's label vocabulary sits outside the current keyword set.

---

---

## Attempt 5: Protinex Rich Chocolate Flavour, 400 g (5 independent photos of the same physical product)

Five real photos of one product, each submitted as its **own independent
scan** — no OCR text or fields were combined across images, per an explicit
constraint on this attempt. Rule pack for all five: version 1, hash
`f7be6482b898559d...`.

| Photo | OCR mean conf. | Fields found | Verdict |
|---|---|---|---|
| img1_front (branding) | 71.9% | 0 of 7 | REVIEW |
| img2_ingredients (side panel) | 70.1% | manufacturer (45.5%, gated to REVIEW) | REVIEW |
| img3_nutrition (nutrition table) | 76.9% | net_quantity = "400g -" (68.0%) → **PASS** | REVIEW |
| img4_usage (instructions) | 79.1% | 0 of 7 | REVIEW |
| img5_bottom_stamp (batch/date/price) | 33.9% | 0 of 7 | REVIEW |

**Diagnosis:** this product's own packaging design deliberately splits its 6
required declarations across 5 separate physical faces — the nutrition
panel itself prints *"FOR CONSUMER CARE DETAILS SEE SIDE PANEL"* and *"FOR
BATCH NO., MFD, EXPIRY DATE AND MRP... SEE BOTTOM"*. Under PraMaan's
one-photo-per-scan architecture, **no single photo of this product could
ever reach COMPLIANT, regardless of OCR quality** — this is an architecture
limitation (already disclosed for Saffola, Attempt 1), not a per-photo
defect. No false verdicts: the one low-confidence find (manufacturer,
45.5%) was correctly gated to REVIEW rather than a wrong PASS; the one PASS
(net_quantity, "400g", img3) is factually correct against the physical
label ("NET WEIGHT 400 g"). img5's very low OCR confidence (33.9%) was
confirmed **not** an EXIF/rotation issue (the photo carries orientation tag
6, which the existing fix already corrects) — the underlying text is
low-contrast dot-matrix stamping on a curved surface, a genuinely hard OCR
case. img4's consumer-care miss, despite "EMAIL: care.india@danone.com"
being visible in the raw OCR text, traces to a keyword-vocabulary gap (the
line-starting phrase is "FOR YOUR FEEDBACK/QUERIES CONTACT:", not in the
recognised keyword set) compounded by OCR corrupting that exact line.

---

## Attempt 6: Jain Soap (toilet soap, marketed by Marico), 150 g

One real photo of the back declaration panel — the **most complete
single-panel declaration seen in this entire dataset**: all 6 applicable
fields (manufacturer/marketer, generic name "TOILET SOAP", net quantity
"75 g X 2 Units = 150 g", Mfg. Date "03/2025", MRP "₹289.00 (inclusive of
all taxes)", and consumer care contact) are present in one column, in plain
print, on one face.

- Scan `6953891c3ab5494490f1f9368c55421b`, OCR mean confidence **20.6%** —
  the lowest of any real photo tested.
- **0 of 7 fields found.** Raw OCR output is almost entirely noise.
- Overall verdict: REVIEW.

**Root cause, measured directly:** `photo.png` is **500×500 pixels at 72
DPI** — 6 to 10 times smaller on each axis than every other real phone photo
tested in this project (which run 2000px+ on the short edge). At this
resolution the label's small printed text is far below what any OCR engine
can reliably resolve into characters. This is the same "low source
resolution" failure class already documented for four downloaded
product-listing photos in the original validation round (420–651px) — this
image is smaller still. **No fix was attempted**: there is no minimal,
generalizable code change that recovers text detail never captured in the
source pixels; that would require image super-resolution, a major new
capability with no guarantee of recovering genuinely lost information, not a
narrow patch. Full writeup: `jain_soap/evidence.md`.

**This is the most promising re-shoot candidate in the dataset.** If this
exact label were re-photographed at native camera resolution, its
single-column, fully-complete layout gives it a stronger shot at genuine
COMPLIANT than any other product attempted so far.

---

## Overall answer: has any real product reached genuine automatic COMPLIANT?

**No — not across 6 attempts (10 real products/photo-sets, 21 real photos
total), from any of these photos, without weakening any safety mechanism.**
Nothing was force-fixed to make a field match, no keyword list was expanded
mid-attempt, no confidence threshold was touched, and no field was manually
injected. One genuine code fix was made (Attempt 3, Tata Tea) — and that fix
corrected a false NON_COMPLIANT into an honest REVIEW, it did not manufacture
a COMPLIANT. The blocking causes across all attempts fall into six honest,
recurring categories:

1. OCR recognition failure on small/decorative/stylized text (Saffola front,
   Protinex front)
2. Label phrasing outside the current keyword vocabulary ("Distributed by",
   "Imp. by", "For Feedback/Complaint" style headings — Monster Mango,
   Protinex usage panel)
3. Single-character OCR misreads at exact anchor points ("Froduct",
   "orlgin" — Monster Mango)
4. Values printed with no adjacent keyword at all, or split across a
   two-line declaration (Saffola's stamped batch block; fixed for the
   two-line MRP case specifically — Tata Tea)
5. Multi-column OCR interleaving corrupting captured evidence text even when
   the resulting conclusion happens to be correct (Tata Tea)
6. Multi-face label designs where required fields are deliberately spread
   across faces no single photo can capture (Saffola front+back; Protinex's
   5 faces), and pure image-resolution shortfalls (Jain Soap, 500×500px)

None of these are reasons to lower a safety gate — they are reasons a human
reviewer still adds real value today. The single most promising path forward
is a re-shoot of the Jain Soap label at native camera resolution (Attempt 6)
— it is the only attempt so far where the underlying content, not the
pipeline, was the limiting factor.
