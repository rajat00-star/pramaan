"""Department/inspector dashboard: real aggregate queries over real scan data,
not canned numbers."""


def _post(client, path):
    with open(path, "rb") as f:
        return client.post("/api/scans", files={"file": (path.name, f, "image/png")}).json()


def test_dashboard_counts_reflect_real_scans(client, inspector_client, compliant_label_path, noncompliant_label_path):
    before = inspector_client.get("/api/dashboard/summary").json()

    compliant_scan = _post(client, compliant_label_path)
    noncompliant_scan = _post(client, noncompliant_label_path)

    after = inspector_client.get("/api/dashboard/summary").json()

    assert after["total_scans"] == before["total_scans"] + 2
    assert after["compliant"] >= before["compliant"] + 1
    assert after["non_compliant"] >= before["non_compliant"] + 1
    assert compliant_scan["overall_verdict"] == "COMPLIANT"
    assert noncompliant_scan["overall_verdict"] == "NON_COMPLIANT"


def test_dashboard_violation_frequency_includes_known_failure(client, inspector_client, noncompliant_label_path):
    _post(client, noncompliant_label_path)
    summary = inspector_client.get("/api/dashboard/summary").json()
    assert summary["violation_frequency"].get("retail_sale_price", 0) >= 1


def test_dashboard_recent_scans_are_present_and_bounded(client, inspector_client, compliant_label_path):
    for _ in range(3):
        _post(client, compliant_label_path)
    summary = inspector_client.get("/api/dashboard/summary").json()
    assert len(summary["recent_scans"]) <= 10
    assert len(summary["recent_scans"]) >= 1
