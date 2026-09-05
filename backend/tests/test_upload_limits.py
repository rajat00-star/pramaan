"""P0-1: the server must never buffer an arbitrarily large upload.

These tests exercise both defense layers in routes/scan.py:
  - layer 1: a fast Content-Length-based rejection (best-effort, client-declared)
  - layer 2: a hard cap enforced on the actual byte stream as it arrives, which is
    what protects the server when Content-Length is missing or lying

Layer 2 exists because Starlette's own `MultiPartParser(max_part_size=...)` was
verified (see scan.py's `_size_capped_stream` docstring) to only limit ordinary
form FIELDS, not file parts — passing it a cap silently does nothing for uploads.
"""


def test_upload_below_limit_is_accepted(client, compliant_label_path):
    with open(compliant_label_path, "rb") as f:
        response = client.post("/api/scans", files={"file": (compliant_label_path.name, f, "image/png")})
    assert response.status_code == 201
    assert response.json()["status"] == "DONE"


def test_upload_exactly_at_limit_is_accepted(client, override_max_upload_mb):
    # Use max_upload_mb = 1.0 exactly and a payload of exactly 1 MiB so the
    # byte-for-byte boundary comparison isn't at the mercy of float rounding.
    override_max_upload_mb(1.0)
    payload = b"\x89PNG\r\n\x1a\n" + (b"0" * (1024 * 1024 - 8))
    assert len(payload) == 1024 * 1024

    response = client.post("/api/scans", files={"file": ("exact.png", payload, "image/png")})
    # The size gate must accept it (not 413) — whether the pipeline can decode
    # this non-image payload afterwards is a separate, unrelated concern.
    assert response.status_code == 201
    assert response.json()["status"] in ("DONE", "ERROR")


def test_upload_clearly_over_limit_is_rejected_with_413(client, override_max_upload_mb):
    # A generous margin (well beyond the multipart-framing overhead allowance) so
    # this doesn't depend on exact protocol byte-counting — just "meaningfully over."
    override_max_upload_mb(1.0)
    payload = b"0" * (1024 * 1024 + 16 * 1024)

    response = client.post("/api/scans", files={"file": ("over.png", payload, "image/png")})
    assert response.status_code == 413
    assert "max upload size" in response.json()["detail"].lower()


def test_upload_far_above_limit_is_rejected_with_413(client, override_max_upload_mb):
    override_max_upload_mb(0.5)
    payload = b"0" * (5 * 1024 * 1024)

    response = client.post("/api/scans", files={"file": ("huge.png", payload, "image/png")})
    assert response.status_code == 413


def test_missing_content_length_valid_upload_still_succeeds(client_without_content_length, compliant_label_path):
    with open(compliant_label_path, "rb") as f:
        response = client_without_content_length.post(
            "/api/scans", files={"file": (compliant_label_path.name, f, "image/png")}
        )
    assert response.status_code == 201
    assert response.json()["status"] == "DONE"


def test_missing_content_length_oversized_upload_is_still_rejected(
    client_without_content_length, override_max_upload_mb
):
    # This is the case layer 1 (Content-Length) cannot catch by definition — proves
    # layer 2 alone is sufficient.
    override_max_upload_mb(0.1)  # ~104 KB cap
    payload = b"0" * (2 * 1024 * 1024)  # 2 MB, no Content-Length header sent

    response = client_without_content_length.post("/api/scans", files={"file": ("stream.png", payload, "image/png")})
    assert response.status_code == 413
    assert "max upload size" in response.json()["detail"].lower()


def test_oversized_upload_never_creates_a_scan_row(client, override_max_upload_mb):
    """A 413 must happen before any Scan row is created — nothing should be left
    stuck in PROCESSING because of a rejected oversized upload."""
    override_max_upload_mb(0.05)
    payload = b"0" * (1024 * 1024)

    before = client.get("/api/scans").json()
    response = client.post("/api/scans", files={"file": ("oversized.png", payload, "image/png")})
    assert response.status_code == 413
    after = client.get("/api/scans").json()
    assert len(after) == len(before)
