# PraMaan SIH Demo Script (3–5 minutes)

Every step below was actually run against the real application during
development — this is a rehearsed sequence, not a hopeful plan.

## Setup (before judges arrive)

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --port 8000
```

Have two browser tabs ready: one for a citizen, one for an inspector. Have a
real packaged product (or two printed label mockups) on hand.

## 1. Citizen flow — photo to verdict (60–90s)

1. Sign in as `citizen_demo` / `citizen123` at `http://localhost:8000`.
2. Upload a label photo. Say aloud: *"This runs real Tesseract OCR, real field
   extraction, and a deterministic rule engine — no AI is deciding
   compliance here."*
3. Point at the verdict banner (COMPLIANT/NON_COMPLIANT/REVIEW — never color
   alone, each has an icon and label).
4. Point at the evidence section: the actual bounding boxes drawn from real
   OCR word coordinates over the actual uploaded image.
5. Point at one rule evaluation row: the exact clause
   (`Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011`), the
   full-sentence reason, and the evidence JSON (OCR'd text + confidence).

**If a field lands in REVIEW** (a good outcome to show, not a failure): point
out that the citizen cannot correct it — no review controls appear for their
role — only cite the field, don't act on it yet.

## 2. Inspector flow — human review + audit (60–90s)

1. In the second tab, sign in as `inspector_demo` / `inspector123`.
2. Upload the same (or a similar low-confidence) label — get the same
   REVIEW verdict.
3. Fill in the corrected value for the flagged field, click "Correct &
   re-check." Watch the verdict banner flip live (e.g. REVIEW → COMPLIANT).
4. Click "Load" under Audit Trail. Point at the full event sequence:
   `SCAN_CREATED → RULES_EVALUATED → SCAN_COMPLETED → FIELD_CORRECTED →
   VERDICT_CHANGED`, each with the actor's user id and a timestamp. Say:
   *"Nothing here can be silently edited — this is an append-only log."*
5. Point at the Review History table: original value, corrected value,
   reviewer, and the verdict transition, side by side.

## 3. Department dashboard (30–45s)

1. Click "Department Dashboard" (visible only for inspector/department_admin
   — say this explicitly: *"A citizen account never sees this tab, and the
   server enforces that even if someone tried to call the API directly."*).
2. Point at the real aggregate counts (they reflect the scans just created,
   live — not canned numbers), the verdict-distribution bar chart, and the
   inspector-activity table (real reviewer, real correction count, real
   timestamp — from the correction just made in step 2).
3. Click any row in "Recent Cases" — a modal opens with the full case: real
   image, extracted fields, legal evaluation, OCR text, audit trail, and a
   "Run replay" button. Click it live: *"Same reproducibility guarantee as
   the CLI, one click away for a department official."*
4. Point at "Rule pack in force" — version, effective date, and the SHA-256
   hash, matching what `/api/rules` and every scan's stored `rule_pack_hash`
   report.

## 3a. Mobile app (optional, 45–60s, if a phone/simulator is available)

The same Citizen and Inspector flows exist in one React Native/Expo app
(`frontend/mobile/`) — see `docs/mobile.md` for setup. If time allows: sign
in as `citizen_demo` on the phone, scan a real product, show the same real
verdict + evidence rendering as the web app; then sign in as
`inspector_demo`, open the review queue, correct a field, and show it land
in the web Department Dashboard's audit trail live — proving both clients
share one backend and one source of truth, not two separate systems.

## 4. Reproducibility (30–45s) — the hardest technical claim, proven live

This is the strongest answer to "how do you know old verdicts don't change
when the law changes?" Have this ready if a judge asks, or lead with it if
time allows:

*"Every scan stores the exact rule-pack version and a content hash of the
legal file it was evaluated against. This endpoint proves it —"*

```bash
curl http://localhost:8000/api/scans/<a scan id>/replay -H "Authorization: Bearer <inspector token>"
```

Point at `reproduced: true` and `replayed_rule_pack_hash` matching the
scan's original `rule_pack_hash`. Explain: *"This re-locates the exact
historical rule file by content hash and re-evaluates the original extracted
data against it — it doesn't just trust a version number."*

## 5. Closing line

*"PraMaan doesn't ask AI what the law means. It turns the law into a
verifiable decision system."* — point at the rule pack file itself
(`docs/legal/rule_pack_v1.json`) if a judge wants to see it's really data,
not a black box.

## Anticipated hard questions and where the answer lives

| Question | Answer |
|---|---|
| "What stops an LLM from hallucinating a violation?" | There's no LLM in the decision path — `rule_engine.py` is pure control flow over JSON data. |
| "How do you know old verdicts don't change when the law changes?" | §4 above — `/replay`, proven with a real (temp, non-legal) v1→v2 test in `tests/test_rule_pack_reproducibility.py`. |
| "What happens with a huge/malformed image?" | Handled gracefully — `docs/security.md`, tested with a genuine decompression bomb. |
| "Why Tesseract, not the PaddleOCR you pitched?" | `README.md` §6 — an honest, swappable-interface decision, not a silent substitution. |
| "Do you support Hindi?" | Real OCR yes, keyword extraction yes for 7 field-anchor phrases — with a measured (not hidden) mixed-script digit-accuracy weakness. See `docs/architecture.md` §7. |
| "Is this production-ready?" | No — see `README.md` §14 for the itemized, honest list of what isn't (queue architecture, migrations, YOLO, full multilingual coverage). |
