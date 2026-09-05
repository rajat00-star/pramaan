"""Authentication and role-based authorization.

Every check here hits the real HTTP API with the real JWT flow — nothing is
mocked. Role is always read server-side from the token's `sub` -> the User row
in the database, never trusted from client input.
"""


def test_login_succeeds_with_correct_demo_credentials(anonymous_client):
    response = anonymous_client.post("/api/auth/login", data={"username": "citizen_demo", "password": "citizen123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "citizen"
    assert body["access_token"]


def test_login_fails_with_wrong_password(anonymous_client):
    response = anonymous_client.post("/api/auth/login", data={"username": "citizen_demo", "password": "wrong"})
    assert response.status_code == 401


def test_login_fails_for_unknown_username(anonymous_client):
    response = anonymous_client.post("/api/auth/login", data={"username": "nobody", "password": "whatever"})
    assert response.status_code == 401


def test_unknown_user_and_wrong_password_give_identical_error(anonymous_client):
    # Prevents username enumeration via a differing error message.
    r1 = anonymous_client.post("/api/auth/login", data={"username": "nobody", "password": "x"})
    r2 = anonymous_client.post("/api/auth/login", data={"username": "citizen_demo", "password": "wrong"})
    assert r1.json()["detail"] == r2.json()["detail"]


def test_me_returns_the_authenticated_users_identity(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "citizen_demo"
    assert body["role"] == "citizen"


def test_me_requires_authentication(anonymous_client):
    assert anonymous_client.get("/api/auth/me").status_code == 401


def test_invalid_bearer_token_is_rejected(anonymous_client):
    anonymous_client.headers.update({"Authorization": "Bearer not-a-real-token"})
    assert anonymous_client.get("/api/auth/me").status_code == 401


def test_missing_bearer_scheme_is_rejected(anonymous_client):
    anonymous_client.headers.update({"Authorization": "not-even-bearer-format"})
    assert anonymous_client.get("/api/auth/me").status_code == 401


# --- role-based access control ------------------------------------------------------


def test_citizen_cannot_access_dashboard(client):
    assert client.get("/api/dashboard/summary").status_code == 403


def test_inspector_can_access_dashboard(inspector_client):
    assert inspector_client.get("/api/dashboard/summary").status_code == 200


def test_admin_can_access_dashboard(admin_client):
    assert admin_client.get("/api/dashboard/summary").status_code == 200


def test_citizen_cannot_access_audit_trail(client):
    # Use a scan id that doesn't need to exist — authorization is checked before
    # any ownership/existence lookup for this role-gated endpoint.
    assert client.get("/api/scans/nonexistent/audit").status_code == 403


def test_inspector_can_access_audit_trail_for_a_real_scan(client, inspector_client, compliant_label_path):
    with open(compliant_label_path, "rb") as f:
        scan = client.post("/api/scans", files={"file": (compliant_label_path.name, f, "image/png")}).json()
    response = inspector_client.get(f"/api/scans/{scan['id']}/audit")
    assert response.status_code == 200
    events = [e["event_type"] for e in response.json()]
    assert "SCAN_CREATED" in events
    assert "SCAN_COMPLETED" in events


def test_unauthenticated_cannot_access_any_protected_route(anonymous_client):
    for path in ("/api/scans", "/api/dashboard/summary", "/api/scans/x/audit", "/api/scans/x/replay"):
        assert anonymous_client.get(path).status_code == 401
