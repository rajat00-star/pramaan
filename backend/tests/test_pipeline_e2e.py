"""The most important test in this repo: a real image goes in, real Tesseract OCR
runs on it, the deterministic rule engine evaluates it against the verified
rule_pack_v1.json, and a legally-traceable verdict comes out — over the actual
HTTP API, exactly as a client would call it. Nothing here is mocked.
"""

import json


def _post_scan(client, image_path, content_type="image/png"):
    with open(image_path, "rb") as f:
        response = client.post("/api/scans", files={"file": (image_path.name, f, content_type)})
    assert response.status_code == 201, response.text
    return response.json()


def _print_verdict_report(label: str, scan: dict) -> None:
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    print(f"VERDICT: {scan['overall_verdict']}   (scan {scan['id']}, confidence "
          f"{scan['overall_confidence']:.1f}%, rule-pack v{scan['rule_pack_version']} "
          f"{scan['rule_pack_hash'][:12]}…)")
    print("-" * 70)
    print("RAW OCR TEXT:")
    print(scan["raw_ocr_text"])
    print("-" * 70)
    for ev in scan["evaluations"]:
        print(f"[{ev['status']:^14}] {ev['field_id']:<28} {ev['legal_reference']}")
        print(f"    reason:   {ev['reason']}")
        print(f"    evidence: {json.dumps(ev['evidence'])}")
    print("=" * 70)


def test_compliant_label_end_to_end(client, compliant_label_path):
    scan = _post_scan(client, compliant_label_path)
    _print_verdict_report("COMPLIANT FIXTURE", scan)

    assert scan["status"] == "DONE"
    assert scan["raw_ocr_text"].strip() != ""

    statuses = {ev["field_id"]: ev["status"] for ev in scan["evaluations"]}
    # Domestic product in this fixture -> country_of_origin must be skipped, not failed/reviewed.
    assert statuses["country_of_origin"] == "NOT_APPLICABLE"

    assert scan["overall_verdict"] == "COMPLIANT", (
        f"expected COMPLIANT, got {scan['overall_verdict']} — per-field statuses: {statuses}"
    )
    assert all(s in ("PASS", "NOT_APPLICABLE") for s in statuses.values())


def test_noncompliant_label_end_to_end(client, noncompliant_label_path):
    scan = _post_scan(client, noncompliant_label_path)
    _print_verdict_report("NON-COMPLIANT FIXTURE", scan)

    assert scan["status"] == "DONE"
    assert scan["overall_verdict"] == "NON_COMPLIANT"

    mrp_eval = next(ev for ev in scan["evaluations"] if ev["field_id"] == "retail_sale_price")
    assert mrp_eval["status"] == "FAIL"
    assert "6(1)(e)" in mrp_eval["legal_reference"]
    assert "inclusive of all taxes" in mrp_eval["reason"].lower()
    assert mrp_eval["evidence"]["raw_value"] is not None

    mrp_field = next(f for f in scan["fields"] if f["field_id"] == "retail_sale_price")
    assert "150.00" in mrp_field["raw_value"]
    assert mrp_field["bbox"] is not None  # evidence bounding box present


def test_human_review_corrects_a_low_confidence_or_missing_field(client, inspector_client, noncompliant_label_path):
    scan = _post_scan(client, noncompliant_label_path)  # citizen creates the scan
    review_target = next((ev for ev in scan["evaluations"] if ev["status"] == "REVIEW"), None)
    if review_target is None:
        # OCR was clean enough that nothing landed in REVIEW for this fixture; still
        # exercise the review endpoint against the one confirmed FAIL to prove the
        # correction -> re-evaluation -> audit-trail path works end-to-end.
        review_target = next(ev for ev in scan["evaluations"] if ev["field_id"] == "retail_sale_price")

    field_id = review_target["field_id"]
    previous_verdict = scan["overall_verdict"]
    corrected_value = "Rs. 150.00 (inclusive of all taxes)"
    # Review is an inspector/department_admin action, not a citizen one.
    response = inspector_client.post(
        f"/api/scans/{scan['id']}/review",
        json={"field_id": field_id, "corrected_value": corrected_value},
    )
    assert response.status_code == 200, response.text
    updated = response.json()

    updated_eval = next(ev for ev in updated["evaluations"] if ev["field_id"] == field_id)
    assert updated_eval["status"] == "PASS"

    review_row = next(r for r in updated["reviews"] if r["field_id"] == field_id)
    assert review_row["corrected_value"] == corrected_value
    assert review_row["reviewer"] == "inspector_demo"  # server-set from the authenticated session, not client input
    assert review_row["previous_verdict"] == previous_verdict
    assert review_row["resulting_verdict"] == updated["overall_verdict"]

    # Full re-fetch (as the citizen owner) proves the correction and new verdict
    # were actually persisted, not just returned once from the review response.
    refetched = client.get(f"/api/scans/{scan['id']}").json()
    assert refetched["overall_verdict"] == updated["overall_verdict"]
    assert len(refetched["reviews"]) == 1


def test_citizen_cannot_submit_a_review(client, noncompliant_label_path):
    scan = _post_scan(client, noncompliant_label_path)
    field_id = scan["evaluations"][0]["field_id"]
    response = client.post(
        f"/api/scans/{scan['id']}/review", json={"field_id": field_id, "corrected_value": "anything"}
    )
    assert response.status_code == 403


def test_citizen_cannot_see_another_citizens_scan(client, noncompliant_label_path, second_citizen_client):
    scan = _post_scan(client, noncompliant_label_path)
    response = second_citizen_client.get(f"/api/scans/{scan['id']}")
    assert response.status_code == 404  # not 403 — existence is not confirmed to a non-owner either

    listing = second_citizen_client.get("/api/scans").json()
    assert all(s["id"] != scan["id"] for s in listing)


def test_wrong_password_is_rejected(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", data={"username": "citizen_demo", "password": "definitely-wrong"}
    )
    assert response.status_code == 401


def test_unauthenticated_request_is_rejected(anonymous_client):
    response = anonymous_client.get("/api/scans")
    assert response.status_code == 401


def test_unreadable_image_is_handled_gracefully(client, tmp_path):
    garbage_path = tmp_path / "not_an_image.png"
    garbage_path.write_bytes(b"this is not a real image file, just bytes")
    scan = _post_scan(client, garbage_path)
    assert scan["status"] == "ERROR"
    assert scan["error_message"]
    assert scan["overall_verdict"] is None


def test_empty_upload_is_rejected(client, tmp_path):
    empty_path = tmp_path / "empty.png"
    empty_path.write_bytes(b"")
    with open(empty_path, "rb") as f:
        response = client.post("/api/scans", files={"file": ("empty.png", f, "image/png")})
    assert response.status_code == 422


def test_unsupported_content_type_is_rejected(client, tmp_path):
    fake_path = tmp_path / "doc.pdf"
    fake_path.write_bytes(b"%PDF-1.4 not really a pdf but wrong type")
    with open(fake_path, "rb") as f:
        response = client.post("/api/scans", files={"file": ("doc.pdf", f, "application/pdf")})
    assert response.status_code == 415
