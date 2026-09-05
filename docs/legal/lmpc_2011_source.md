# Source of truth: Legal Metrology (Packaged Commodities) Rules, 2011

## Provenance

| | |
|---|---|
| Primary document used | "Book on Legal Metrology Packaged Commodities Rules, 2011 with all amendments" |
| Host | consumeraffairs.gov.in (Dept. of Consumer Affairs, Govt. of India) |
| URL | https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/Book_on_Legal_Metrology_Packaged_Commodities_Rules,2011_with_all_amendments_whatsnews.pdf |
| Document metadata | Created 6 May 2022, modified 9 May 2022 (per PDF properties) — **stale relative to 2026 amendments** |
| Local copy | downloaded and text-extracted for this rule pack; re-verify against the live URL before demo day in case the department republishes |

**Known gap, load-bearing for the architecture:** this compiled PDF is the department's own consolidated text, but it has not been updated since mid-2022. Two amendments the deck cites — and which independently verify as real via third-party legal-update trackers (SCC Online, TeamLease RegTech, Mondaq, Digital Policy Alert) — are **not** reflected in it:

- **Legal Metrology (Packaged Commodities) Amendment Rules, 2026** — notified 13 Feb 2026, effective 1 Jul 2026 (later modified by a Second Amendment on 27 Apr 2026, effective 1 Jul 2027). Inserts sub-rule **6(10A)**: e-commerce entities selling imported products must expose a searchable/sortable country-of-origin filter on listings. This is a **platform/listing-level** requirement, not a physical-label requirement — out of scope for a photo-based label scanner.
- **Legal Metrology (Packaged Commodities) Third Amendment Rules, 2026** — notified 29 May 2026, effective 1 Jun 2026. Amends Rule 4 (bonded-warehouse declaration timing for importers) and Rule 27 (registration/accountability). Not label-content-relevant either.

Neither 2026 amendment touches Rule 6(1)(a)–(g), Rule 6(2), Rule 22, or the First Schedule tolerance tables used below — so the MVP rule pack below is current as of 2026-09-04. **Engineering implication:** "versioned rule engine" cannot mean "point at this one PDF." The real amendment feed has to be the e-Gazette / PIB notification stream (or a paid aggregator), because the department's own consolidated document lags real amendments by years. Flag this to judges proactively — it's a stronger answer than pretending the static PDF is sufficient.

## Rule 6 — Declarations to be made on every package (verbatim, with amendment history)

> *(1) Every package shall bear thereon or on label securely affixed thereto, a definite, plain and conspicuous declaration...*

**6(1)(a)** — Name and address of the manufacturer, or (if manufacturer ≠ packer) both manufacturer and packer; for imported packages, name and address of the importer.
- Explanation I: unqualified name/address on label is presumed to be the manufacturer's.
- Explanation II: if a brand owner's name/address appears as marketer, brand owner is liable.
- Explanation III: food articles are governed by the Food Safety and Standards Act, 2006 instead (substituted vide G.S.R. 427(E), 5 Jun 2012, replacing the earlier reference to the Prevention of Food Adulteration Act, 1954).

**6(1)(aa)** — Country of origin/manufacture/assembly for imported products. *(Inserted vide GSR 629(E), 23 Jun 2017, effective 1 Jan 2018.)*

**6(1)(b)** — Common or generic name of the commodity; for multi-product packages, name and quantity of each product.

**6(1)(c)** — Net quantity, in standard unit of weight/measure, or number if sold by count.

**6(1)(d)** — Month and year of manufacture/pre-pack/import.
- Food articles: governed by FSSA 2006 instead.
- Seeds certified under the Seeds Act, 1966: exempt.
- Cosmetics: governed by Drugs and Cosmetics Rules, 1945 instead.
- Exempt entirely: bidi/incense-stick packages; 14.2kg/5kg domestic LPG cylinders marketed by PSUs.
- *(The "or pre-packed or imported" wording was removed vide GSR 779(E), 2 Nov 2021, effective 1 Apr 2022 per the original notification, later deferred to 1 Oct 2022 vide GSR 226(E), 28 Mar 2022 — track this as an example of an effective-date being amended by a *second* notification.)*

**6(1)(da)** — "Best before or use by" date/month/year, for commodities that can become unfit for consumption. *(Inserted vide GSR 629(E), 23 Jun 2017, effective 1 Jan 2018.)*

**6(1)(e)** — Retail sale price: must state "Maximum Retail Price... inclusive of all taxes," in Indian currency. *(Substituted vide GSR 629(E), 23 Jun 2017; further amended vide GSR 779(E), 2 Nov 2021 effective 1 Apr 2022 / GSR 226(E) 28 Mar 2022.)*
- Exempt: bidi packages; LPG cylinders under Administrative Price Mechanism.
- Alcoholic beverages: governed by State Excise law instead, unless that law is silent on MRP.

**6(1)(f)** — Dimensions of the commodity, where size is relevant and pieces differ.

**6(1)(g)** — Any other matter specified elsewhere in the Rules.

**6(2)** — Name, address, telephone number, and (if available) e-mail of the consumer-complaints contact. *(Substituted vide GSR 385(E), 14 May 2015, effective 1 Jan 2016.)*

**6(3)/(4)** — Stickers cannot be used to alter/add a mandatory declaration (an MRP-reduction sticker is the sole exception); stickers *can* be used for non-mandatory information.

**6(4A)** — Optional additions permitted: barcode/GTIN/QR code, e-code for net-quantity assurance, authorised government-scheme logos. *(Inserted vide GSR 629(E), 23 Jun 2017, effective 1 Jan 2018.)*

## Rule 22 — Maximum permissible error

> *(1) The maximum permissible error in relation to the commodities shall be such as is indicated in the First Schedule.*

Establishes that tolerance accounts for (a) unavoidable weighing/measuring deviation in good packaging practice, (b) ordinary transport/storage/climate exposure, (c) packaging-material effects. Rule 23 separately defines a **deceptive package** (misleading size impression despite correct declared quantity) as a distinct violation from short-fill.

## First Schedule — Table I: permissible error on net quantity by weight/volume

Source: First Schedule, para 1, Table I (verbatim, units g/ml):

| Declared quantity (g or ml) | Max permissible error, in excess or deficiency |
|---|---|
| up to 50 | 9% of declared quantity |
| 50 to 100 | 4.5 g/ml (absolute) |
| 100 to 200 | 4.5% of declared quantity |
| 200 to 300 | 9 g/ml (absolute) |
| 300 to 500 | 3% of declared quantity |
| 500 to 1000 | 15 g/ml (absolute) |
| 1000 to 10000 | 1.5% of declared quantity |
| 10000 to 15000 | 150 g/ml (absolute) |
| more than 15000 | 1.0% of declared quantity |

Rounding rule: percentage-based error rounds to nearest 0.1 g/ml for declared quantity ≤ 1000 g/ml, and to the next whole g/ml above 1000 g/ml.

## First Schedule — Table II: permissible error by length, area or number

| Declared in | Max permissible error |
|---|---|
| units of length | 2% up to 10 m, then 1% above 10 m |
| units of area | 4% up to 10 m², then 1% above 10 m² |
| number | 2% of declared quantity |

## What this rules out for MVP

Table I/II give a **band lookup + arithmetic tolerance check** — genuinely conditional logic, not a presence check. This is the strongest MVP field for proving "deterministic legal computation," and it needs the *declared* quantity as the band key, so the OCR'd/extracted net-quantity value must carry its unit (g/ml/number/m/m²) correctly for band lookup to be correct — a real extraction-quality dependency worth calling out to judges.
