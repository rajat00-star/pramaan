"""Historical rule-version reproducibility, proven through the REAL HTTP API end
to end — not just unit-level function calls (see test_rule_pack_integrity.py for
those). This builds two rule-pack files in a throwaway temp directory (never
touching docs/legal/rule_pack_v1.json) and drives real scans against each via
the running app, exactly as a deployment introducing a real v2 would.

TEST 1: same input, same rule version, twice -> identical result.
TEST 2: input evaluated under v1 -> the v1-specific result.
TEST 3: introducing v2 with a changed parameter -> a different result for new scans.
TEST 4: the v1 scan's stored result is untouched after v2 becomes active.
TEST 5: replaying the v1 scan reproduces its original result exactly.
"""

import json
from pathlib import Path

from app.config import get_settings
from app.main import app as fastapi_app

LABEL_LINES = [
    "Manufactured by: Versioning Test Co, 1 Test Street, Delhi 110001",
    "Product: Test Widgets",
    "Net Qty: 10 nos",
    "Mfg Date: 01/2026",
    "MRP Rs. 500.00 incl. of all taxes",
    "Customer Care: 1800-000-0000, care@versioningtest.example.com",
]


def _make_versioned_rule_packs(tmp_path: Path) -> tuple[Path, Path]:
    real_data = json.loads(get_settings().rule_pack_path.read_bytes())

    v1_path = tmp_path / "rule_pack_v1.json"
    v1_path.write_text(json.dumps(real_data))

    v2_data = json.loads(json.dumps(real_data))  # deep copy
    v2_data["rule_pack_version"] = "2"
    net_qty = next(f for f in v2_data["fields"] if f["field_id"] == "net_quantity")
    net_qty["tolerance_table_length_area_number"]["entries"]["number"]["percentage"] = 9.0
    v2_path = tmp_path / "rule_pack_v2.json"
    v2_path.write_text(json.dumps(v2_data))

    return v1_path, v2_path


def _activate_rule_pack(path: Path) -> None:
    base_settings = get_settings()
    fastapi_app.dependency_overrides[get_settings] = lambda: base_settings.model_copy(
        update={"rule_pack_path": path}
    )


def _post_scan(client, tmp_path: Path, name: str) -> dict:
    image_path = tmp_path / name
    from tests.conftest import render_label

    render_label(LABEL_LINES, image_path)
    with open(image_path, "rb") as f:
        response = client.post("/api/scans", files={"file": (name, f, "image/png")})
    assert response.status_code == 201, response.text
    return response.json()


def _net_qty_pct(scan: dict) -> float:
    ev = next(e for e in scan["evaluations"] if e["field_id"] == "net_quantity")
    return ev["evidence"]["applicable_tolerance"]["pct"]


def test_full_v1_to_v2_reproducibility_flow(client, inspector_client, tmp_path):
    v1_path, v2_path = _make_versioned_rule_packs(tmp_path)

    try:
        # --- v1 is active: create a scan, and prove same-version determinism ---
        _activate_rule_pack(v1_path)
        scan_v1 = _post_scan(client, tmp_path, "v1_scan.png")
        assert scan_v1["rule_pack_version"] == "1"
        assert scan_v1["overall_verdict"] == "COMPLIANT"
        assert _net_qty_pct(scan_v1) == 2.0  # the real, unmodified legal value

        # TEST 1: same input, same active version, evaluated again -> identical result
        scan_v1_repeat = _post_scan(client, tmp_path, "v1_scan_repeat.png")
        assert scan_v1_repeat["overall_verdict"] == scan_v1["overall_verdict"]
        assert _net_qty_pct(scan_v1_repeat) == _net_qty_pct(scan_v1)
        assert scan_v1_repeat["rule_pack_hash"] == scan_v1["rule_pack_hash"]

        # --- v2 becomes active: TEST 3, a new scan sees the new parameter ---
        _activate_rule_pack(v2_path)
        scan_v2 = _post_scan(client, tmp_path, "v2_scan.png")
        assert scan_v2["rule_pack_version"] == "2"
        assert _net_qty_pct(scan_v2) == 9.0  # different result under v2
        assert scan_v2["rule_pack_hash"] != scan_v1["rule_pack_hash"]

        # TEST 4: the ORIGINAL v1 scan, re-fetched now that v2 is active, is untouched
        refetched_v1 = client.get(f"/api/scans/{scan_v1['id']}").json()
        assert refetched_v1["rule_pack_version"] == "1"
        assert refetched_v1["rule_pack_hash"] == scan_v1["rule_pack_hash"]
        assert _net_qty_pct(refetched_v1) == 2.0
        assert refetched_v1["overall_verdict"] == "COMPLIANT"

        # TEST 5: replay reproduces the ORIGINAL verdict, locating v1 by hash even
        # though v2 is the currently-active rule pack.
        replay = inspector_client.get(f"/api/scans/{scan_v1['id']}/replay").json()
        assert replay["reproduced"] is True
        assert replay["replayed_rule_pack_version"] == "1"
        assert replay["replayed_rule_pack_hash"] == scan_v1["rule_pack_hash"]
        assert replay["replayed_overall_verdict"] == scan_v1["overall_verdict"]

        # Replaying the v2 scan (still active) reproduces ITS result too.
        replay_v2 = inspector_client.get(f"/api/scans/{scan_v2['id']}/replay").json()
        assert replay_v2["reproduced"] is True
        assert replay_v2["replayed_rule_pack_version"] == "2"
    finally:
        fastapi_app.dependency_overrides.pop(get_settings, None)


def test_replay_requires_inspector_or_admin_role(client, compliant_label_path):
    with open(compliant_label_path, "rb") as f:
        scan = client.post("/api/scans", files={"file": (compliant_label_path.name, f, "image/png")}).json()
    assert client.get(f"/api/scans/{scan['id']}/replay").status_code == 403
