"""Regression tests for the golden SIH demo dataset (docs/demo/golden_dataset/).

These tests run the same images stored in that dataset through the real
pipeline (OCR -> extraction -> rule engine, via the actual HTTP API, exactly
like every other scan) and assert the verdicts stay what the demo claims they
are. They exist so a future change to extraction, OCR, or the rule engine
cannot silently break the golden demo without a test failure calling it out.

No test here special-cases these images by id, filename, or content — they go
through `POST /api/scans` and `evaluate_all`/`aggregate_verdict_from_statuses`
exactly like any other upload. `test_no_demo_specific_bypass_exists` verifies
that directly by scanning the production pipeline source for hardcoded
references to this dataset.
"""

import json

import pytest

from app.config import REPO_ROOT, get_settings
from app.pipeline import rule_engine

GOLDEN_DIR = REPO_ROOT / "docs" / "demo" / "golden_dataset"
NON_COMPLIANT_IMAGE = GOLDEN_DIR / "non_compliant_test_label" / "label.png"
REVIEW_IMAGE = GOLDEN_DIR / "review_myfitness" / "photo.jpg"
MANIFEST_PATH = GOLDEN_DIR / "golden_demo_manifest.json"


def _post_scan(client, image_path):
    with open(image_path, "rb") as f:
        response = client.post("/api/scans", files={"file": (image_path.name, f, "image/jpeg")})
    assert response.status_code == 201, response.text
    return response.json()


def test_golden_manifest_is_valid_json_and_matches_live_rule_pack():
    manifest = json.loads(MANIFEST_PATH.read_text())
    live_rule_pack = rule_engine.load_rule_pack(str(get_settings().rule_pack_path))
    assert manifest["rule_pack_version"] == live_rule_pack.version
    assert manifest["rule_pack_hash"] == live_rule_pack.sha256_hash


def test_golden_non_compliant_case_remains_non_compliant(client):
    scan = _post_scan(client, NON_COMPLIANT_IMAGE)
    statuses = {e["field_id"]: e["status"] for e in scan["evaluations"]}

    assert scan["overall_verdict"] == "NON_COMPLIANT", (
        f"golden NON_COMPLIANT demo case regressed — got {scan['overall_verdict']}, statuses: {statuses}"
    )
    # The violation must stay isolated to retail_sale_price (missing "inclusive
    # of all taxes") — every other applicable field must stay PASS/NOT_APPLICABLE,
    # so this stays a clean single-violation demo rather than an accidental
    # multi-field failure that would obscure which rule was actually violated.
    assert statuses["retail_sale_price"] == "FAIL"
    for field_id, status in statuses.items():
        if field_id != "retail_sale_price":
            assert status in ("PASS", "NOT_APPLICABLE"), f"unexpected {field_id}={status}"


def test_golden_review_case_remains_review(client):
    scan = _post_scan(client, REVIEW_IMAGE)
    statuses = {e["field_id"]: e["status"] for e in scan["evaluations"]}

    assert scan["overall_verdict"] == "REVIEW", (
        f"golden REVIEW demo case regressed — got {scan['overall_verdict']}, statuses: {statuses}"
    )
    # Guards the specific defect this exact photo previously exposed: a
    # punctuation-only OCR capture must never be reported as a found
    # net_quantity value (which previously produced a false NON_COMPLIANT).
    found_fields = {f["field_id"]: f for f in scan["fields"]}
    assert found_fields["net_quantity"]["found"] is False


def test_golden_review_case_scan_records_exact_rule_pack_version_and_can_replay(client, inspector_client):
    scan = _post_scan(client, REVIEW_IMAGE)
    live_rule_pack = rule_engine.load_rule_pack(str(get_settings().rule_pack_path))

    assert scan["rule_pack_version"] == live_rule_pack.version
    assert scan["rule_pack_hash"] == live_rule_pack.sha256_hash

    replay = inspector_client.get(f"/api/scans/{scan['id']}/replay")
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()
    assert replay_body["reproduced"] is True
    assert replay_body["replayed_overall_verdict"] == replay_body["original_overall_verdict"] == "REVIEW"


def test_golden_review_case_human_correction_workflow_reaches_final_deterministic_state(client, inspector_client):
    """Reproduces the review_myfitness/evidence.md workflow: correct every
    field legible on the physical package, leave the rest alone, and confirm
    the final verdict is derived the same deterministic way as the initial one
    — not hand-set by the correction endpoint."""
    scan = _post_scan(client, REVIEW_IMAGE)
    scan_id = scan["id"]

    corrections = [
        ("net_quantity", "510 g"),
        ("date_of_manufacture", "03.08.2026"),
        ("retail_sale_price", "Rs. 319.00 (Inclusive of all taxes)"),
    ]
    for field_id, corrected_value in corrections:
        response = inspector_client.post(
            f"/api/scans/{scan_id}/review",
            json={"field_id": field_id, "corrected_value": corrected_value, "note": "test verification"},
        )
        assert response.status_code == 200, response.text

    final = inspector_client.get(f"/api/scans/{scan_id}").json()
    final_statuses = {e["field_id"]: e["status"] for e in final["evaluations"]}
    assert final_statuses["net_quantity"] == "PASS"
    assert final_statuses["date_of_manufacture"] == "PASS"
    assert final_statuses["retail_sale_price"] == "PASS"
    # common_generic_name and manufacturer_packer_importer were never corrected
    # in this reduced reproduction, so REVIEW must persist overall — proving
    # the endpoint recomputes the verdict from all fields' actual statuses
    # rather than flipping to COMPLIANT once "enough" fields are touched.
    assert final["overall_verdict"] == "REVIEW"


@pytest.mark.skip(
    reason=(
        "Golden COMPLIANT case is intentionally not yet demonstrated with a real "
        "product photo — see docs/demo/golden_dataset/compliant_pending/README.md. "
        "This test is a placeholder so the gap stays visible in test output "
        "rather than silently missing from the suite."
    )
)
def test_golden_compliant_case_remains_compliant():
    pass


def test_no_demo_specific_bypass_exists():
    """The golden dataset's ids, filenames, and product names must not appear
    anywhere in the production pipeline/rule-engine/route source — a verdict
    must only ever come from OCR + extraction + the data-driven rule pack,
    never from a check against this specific demo."""
    forbidden_strings = [
        "golden_dataset",
        "golden_demo",
        "non_compliant_test_label",
        "review_myfitness",
        "myfitness",
        "8fec5491e60c481aa33a6c9ed06369bc",  # non-compliant golden scan id
        "b1891bebc9e942abba8c2ff818b2c363",  # review golden scan id
    ]
    production_source_dirs = [
        REPO_ROOT / "backend" / "app" / "pipeline",
        REPO_ROOT / "backend" / "app" / "routes",
        REPO_ROOT / "backend" / "app" / "models.py",
        REPO_ROOT / "backend" / "app" / "auth.py",
    ]

    checked_any_file = False
    for target in production_source_dirs:
        py_files = [target] if target.is_file() else list(target.rglob("*.py"))
        for py_file in py_files:
            checked_any_file = True
            text = py_file.read_text().lower()
            for forbidden in forbidden_strings:
                assert forbidden.lower() not in text, (
                    f"found forbidden demo-specific reference '{forbidden}' in {py_file} — "
                    "the rule engine and pipeline must never special-case the golden demo dataset"
                )
    assert checked_any_file, "no production source files were actually scanned — test setup is broken"
