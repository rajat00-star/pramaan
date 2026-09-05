import os
import tempfile
import uuid
from pathlib import Path

# Point the app at an isolated DB + upload dir *before* app.config is imported anywhere,
# so the lru_cache'd Settings singleton never picks up a developer's real pramaan.db.
_TEST_STATE_DIR = Path(tempfile.mkdtemp(prefix="pramaan_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_STATE_DIR / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(_TEST_STATE_DIR / "uploads")
os.environ["SECRET_KEY"] = "test-only-secret-key-do-not-use-in-production"

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.auth import seed_demo_users
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.main import app as fastapi_app

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Volumes/Data/opt/anaconda3/envs/ai/lib/python3.11/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def render_label(lines: list[str], path: Path, width: int = 1400, height: int = 900) -> Path:
    font = _load_font(28)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 50
    for line in lines:
        draw.text((50, y), line, fill="black", font=font)
        y += 70
    img.save(path)
    return path


_DEVANAGARI_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",  # macOS
    "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",  # Linux (apt: fonts-noto-devanagari)
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
]


def _find_devanagari_font(size: int) -> ImageFont.FreeTypeFont | None:
    for candidate in _DEVANAGARI_FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return None


def render_hindi_label(lines: list[str], path: Path, width: int = 1300, height: int = 500) -> Path:
    """Renders with a real Devanagari-capable font — skips the test (not a hard
    failure) if this environment has none installed, rather than either faking
    Hindi text with a Latin font (which would render as boxes) or failing CI for
    a missing optional font package."""
    font = _find_devanagari_font(34)
    if font is None:
        pytest.skip("No Devanagari-capable font found on this system — install one (see CI workflow) to run this test")
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 30
    for line in lines:
        draw.text((30, y), line, fill="black", font=font)
        y += 85
    img.save(path)
    return path


COMPLIANT_LABEL_LINES = [
    "Manufactured by: ULTRON Foods Pvt Ltd, 12 MG Road, Bengaluru 560001",
    "Product: Refined Sunflower Oil",
    "Net Wt: 900 g",
    "Mfg Date: 03/2026",
    "MRP Rs. 180.00 incl. of all taxes",
    "Customer Care: 1800-123-4567, care@ultronfoods.example.com",
]

NONCOMPLIANT_LABEL_LINES = [
    "Manufactured by: Falcon Traders, 45 Ring Road, Pune 411001",
    "Product: Mixed Fruit Jam",
    "Net Wt: 500 g",
    "Mfg Date: 01/2026",
    "MRP Rs. 150.00",
    "Customer Care: 1800-999-8888, help@falcontraders.example.com",
]


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    init_db()
    db = SessionLocal()
    try:
        seed_demo_users(db, get_settings())
    finally:
        db.close()
    yield


def _login(test_client: TestClient, username: str, password: str) -> str:
    response = test_client.post("/api/auth/login", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def anonymous_client() -> TestClient:
    """No Authorization header at all — for testing that protected endpoints
    genuinely reject unauthenticated requests."""
    return TestClient(fastapi_app)


@pytest.fixture()
def client() -> TestClient:
    """Pre-authenticated as the citizen demo account. Most existing tests care
    about pipeline behavior, not the auth layer itself, so this keeps them
    unchanged; auth-specific tests use anonymous_client/inspector_client/
    admin_client explicitly."""
    test_client = TestClient(fastapi_app)
    token = _login(test_client, "citizen_demo", "citizen123")
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


@pytest.fixture()
def inspector_client() -> TestClient:
    test_client = TestClient(fastapi_app)
    token = _login(test_client, "inspector_demo", "inspector123")
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


@pytest.fixture()
def second_citizen_client() -> TestClient:
    """A second, genuinely distinct citizen account (not one of the shared demo
    users) — for proving cross-user IDOR isolation rather than same-user access."""
    from app import auth, models

    db = SessionLocal()
    try:
        username = f"test_citizen_{uuid.uuid4().hex[:8]}"
        password = "test-password-123"
        if not db.query(models.User).filter_by(username=username).first():
            db.add(models.User(username=username, password_hash=auth.hash_password(password), role="citizen"))
            db.commit()
    finally:
        db.close()

    test_client = TestClient(fastapi_app)
    token = _login(test_client, username, password)
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


@pytest.fixture()
def admin_client() -> TestClient:
    test_client = TestClient(fastapi_app)
    token = _login(test_client, "admin_demo", "admin123")
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


@pytest.fixture()
def client_without_content_length() -> TestClient:
    """A client whose outgoing requests never carry a Content-Length header,
    forcing any size-limit logic under test to rely purely on the actual byte
    stream rather than the client's declared length. Pre-authenticated like
    `client`."""
    test_client = TestClient(fastapi_app)
    token = _login(test_client, "citizen_demo", "citizen123")
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    def _strip_content_length(request):
        if "content-length" in request.headers:
            del request.headers["content-length"]
            request.headers["transfer-encoding"] = "chunked"

    test_client.event_hooks = {"request": [_strip_content_length]}
    return test_client


@pytest.fixture()
def override_max_upload_mb():
    """Temporarily override settings.max_upload_mb for one test via FastAPI's
    dependency_overrides, without touching the real lru_cache'd Settings singleton."""

    def _apply(max_upload_mb: float):
        base_settings = get_settings()
        tiny_settings = base_settings.model_copy(update={"max_upload_mb": max_upload_mb})
        fastapi_app.dependency_overrides[get_settings] = lambda: tiny_settings
        return tiny_settings

    yield _apply
    fastapi_app.dependency_overrides.pop(get_settings, None)


@pytest.fixture(scope="session")
def compliant_label_path() -> Path:
    return render_label(COMPLIANT_LABEL_LINES, FIXTURES_DIR / "compliant_label.png")


@pytest.fixture(scope="session")
def noncompliant_label_path() -> Path:
    return render_label(NONCOMPLIANT_LABEL_LINES, FIXTURES_DIR / "noncompliant_label.png")


HINDI_LABEL_LINES = [
    "निर्माता: टेस्ट कंपनी प्राइवेट लिमिटेड, दिल्ली",
    "उत्पाद: सरसों का तेल",
    "शुद्ध वजन: 500 g",
    "अधिकतम खुदरा मूल्य Rs. 120.00",
    "ग्राहक सेवा: 1800-111-2222",
]


@pytest.fixture(scope="session")
def hindi_label_path() -> Path:
    return render_hindi_label(HINDI_LABEL_LINES, FIXTURES_DIR / "hindi_label.png")
