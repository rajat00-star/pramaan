import secrets
import warnings
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
LEGAL_DIR = REPO_ROOT / "docs" / "legal"

# Generated fresh per process if SECRET_KEY isn't set — fine for a demo run (tokens
# just stop validating on restart), but every token issued by this process is
# invalidated on the next restart, and a multi-worker deployment would disagree
# with itself. Production MUST set SECRET_KEY explicitly; see .env.example.
_INSECURE_DEV_SECRET_KEY = secrets.token_hex(32)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'pramaan.db'}"
    rule_pack_path: Path = LEGAL_DIR / "rule_pack_v1.json"
    upload_dir: Path = BACKEND_DIR / "uploads"
    max_upload_mb: float = 10.0
    allowed_content_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")

    tesseract_langs: str = "eng"
    confidence_threshold: float = 60.0

    # Comma-separated in the env var (e.g. "http://localhost:5173,https://pramaan.example.gov.in").
    # Deliberately a plain `str`, not a `tuple`/`list` — pydantic-settings tries to
    # JSON-decode env values for genuinely complex-typed fields, which would crash
    # the app on startup given a comma-separated string (verified directly: this
    # was a real bug caught while writing .env.example, not a hypothetical one).
    # Use `cors_allow_origins_list` below to get the parsed tuple.
    # Defaults to common local-dev origins only — NOT "*" — since authenticated
    # requests carry a bearer token that a permissive CORS policy would expose to
    # any origin able to trick a user's browser into calling this API.
    # :8090 is the mobile app's `expo start --web` dev port (frontend/mobile) —
    # native iOS/Android requests don't go through browser CORS at all, this
    # only matters when exercising the mobile app's web target in development.
    cors_allow_origins: str = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:8090,http://127.0.0.1:8090"

    secret_key: str = _INSECURE_DEV_SECRET_KEY
    access_token_expire_minutes: int = 720  # 12h

    # Seed accounts for local/demo use only: "user:password:role,user2:password2:role2".
    # Never commit real credentials — this is read from the environment (see
    # .env.example) and is empty by default in a fresh checkout.
    demo_users: str = "citizen_demo:citizen123:citizen,inspector_demo:inspector123:inspector,admin_demo:admin123:department_admin"

    @property
    def cors_allow_origins_list(self) -> tuple[str, ...]:
        return tuple(origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip())


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.secret_key == _INSECURE_DEV_SECRET_KEY:
        warnings.warn(
            "SECRET_KEY is not set — using a randomly generated development-only key. "
            "Set SECRET_KEY in the environment before deploying anywhere real.",
            stacklevel=2,
        )
    return settings
