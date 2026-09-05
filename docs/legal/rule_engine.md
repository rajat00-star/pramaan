# The PraMaan Legal Rule Engine

## Source of truth

- [`lmpc_2011_source.md`](lmpc_2011_source.md) — verbatim citations from the actual Legal Metrology (Packaged Commodities) Rules, 2011, transcribed from the Department of Consumer Affairs' own compiled PDF (downloaded, `pdftotext`-extracted, cross-checked — not retyped from memory), with every amendment's G.S.R. number and date.
- [`rule_pack_v1.json`](rule_pack_v1.json) — the machine-readable rule pack the engine actually reads.

Nothing in `backend/app/pipeline/rule_engine.py` is allowed to encode a legal
fact that isn't traceable to one of these two files.

## Why a rule engine and not an LLM

An LLM can be wrong in ways that are hard to detect and impossible to audit —
it might paraphrase a clause incorrectly, apply the wrong version of a rule,
or simply hallucinate a threshold. A deterministic engine over versioned data
is auditable by construction: given the same three inputs (extracted fields,
rule-pack version, rule-pack content), it always produces the same output,
and every branch in the code traces to a specific line in `rule_pack_v1.json`.
This is the load-bearing differentiator of the whole project, not a
nice-to-have.

## Schema

Each field in `rule_pack_v1.json` carries: `field_id`, `clause`, `title`,
`legal_reference`, `check_type`, `condition` (human-readable), and — for
fields with actual numeric thresholds — machine-readable data. Example, the
Table II (First Schedule, count-based tolerance) structure:

```json
"tolerance_table_length_area_number": {
  "schedule": "First Schedule, para 2, Table II",
  "source": "Legal Metrology (Packaged Commodities) Rules, 2011",
  "effective_date": "2011-04-01",
  "entries": {
    "number": {
      "unit": "number",
      "type": "flat_percentage",
      "percentage": 2.0,
      "rule": "2% of declared quantity."
    }
  }
}
```

`rule_engine.lookup_count_tolerance(count, table)` reads `percentage` from
this structure — there is no hardcoded fallback value in Python; the function
has no default for `table` (verified by
`tests/test_rule_pack_integrity.py::test_lookup_count_tolerance_has_no_default_table_parameter`,
which inspects the function signature directly).

## Startup validation — fail loudly, never invent

`load_rule_pack()` calls `_validate_rule_pack()` before returning anything.
Required checks: every field has a non-empty `field_id`/`clause`/
`legal_reference`/`title`/`check_type`; `net_quantity`'s weight/volume table
has valid numeric bands; its Table II `number.percentage` is a positive
number. A violation raises `RulePackValidationError`, and `app/main.py`'s
`lifespan` calls `load_rule_pack()` at **application startup** — a broken
rule pack means the process refuses to start, not "works until the first
scan hits the bad field." Verified directly: pointed `RULE_PACK_PATH` at a
rule pack missing the Table II percentage and ran `uvicorn` — output ended
with `RulePackValidationError: ... must be a positive number (got None)` then
`ERROR: Application startup failed. Exiting.`

## Versioning and reproducibility

Every `Scan` stores `rule_pack_version` (a human-facing label) and
`rule_pack_hash` (SHA-256 of the exact file bytes evaluated against — the
actual reproducibility guarantee, since a version label alone can't prove
content). `POST /api/scans/{id}/review` refuses (`409`) to re-evaluate a scan
against a newer rule pack than the one it was originally scored with — a
historical verdict is never silently re-scored under today's law.

`GET /api/scans/{id}/replay` (inspector/admin) proves this live:
`rule_engine.find_rule_pack_by_hash()` scans the legal directory for any
`rule_pack_v*.json` file matching the scan's stored hash — not "whatever is
currently active" — re-evaluates the scan's original extracted fields against
it, and reports whether the verdict reproduces exactly.

**Current honest state**: only one verified legal version exists
(`rule_pack_v1.json`) — no `rule_pack_v2.json` has been published, because no
verified 2026 amendment to the Legal Metrology Rules changes any of the 7
fields this MVP evaluates (checked directly against the amendments the deck
itself cites — see `lmpc_2011_source.md`'s provenance section). Publishing a
fabricated v2 "for demo purposes" would violate the project's own "never
invent law" principle. Instead, the **versioning mechanism itself** is fully
built and tested: `tests/test_rule_pack_reproducibility.py` constructs a
throwaway v1+v2 pair in a temp directory (never touching the real legal
file), drives real scans against each through the actual HTTP API, and
proves:

1. Same input, same active version, evaluated twice → identical result (same hash, same evidence).
2. A scan evaluated under v1 gets v1's values.
3. Introducing v2 with a changed parameter → a new scan sees the new value.
4. The original v1 scan, re-fetched after v2 becomes active, is provably unchanged.
5. `/replay` reproduces the v1 scan's original verdict by locating v1 by hash, even with v2 now active.

## Known, disclosed limitation

Net-quantity checking validates the **declaration** (is a value present? is
the unit recognized? does it fall into the correct First Schedule band with
correctly-rounded tolerance arithmetic?) — it cannot verify the package's
*actual physical contents* against Rule 22's tolerance without a calibrated
scale, which is out of scope for a photo-only system. This limitation is
written directly into every `net_quantity` evaluation's
`evidence.limitation` field, not hidden in a doc no one reads.

## Clause references are data, not code

Every reason string a verdict produces (`"...as required by Rule 6(1)(e)"`)
interpolates `field_spec['clause']` from the loaded rule pack at evaluation
time. `tests/test_rule_pack_integrity.py` proves this by loading a temporary
rule pack with a clause deliberately renamed to a test marker string
(`"Rule 6(1)(e)-TEST-MARKER"`) and confirming that marker — which appears
nowhere in `rule_engine.py`'s source — shows up in the generated reason.
