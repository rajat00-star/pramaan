# PraMaan Deployment

## Honesty note up front

The Dockerfile and docker-compose.yml below are written against the exact
dependency versions verified to work in local development (including a real
PostgreSQL 16 instance — see README §11), but **Docker itself is not
installed in the environment this project was built in**, so
`docker build`/`docker compose up` have not been executed here. If something
in the Docker path doesn't work on the first try in your environment, that's
the honest reason why — the native setup below is what was actually run.

## Native setup (verified)

```bash
# System dependency: Tesseract OCR + Indic language packs
brew install tesseract tesseract-lang        # macOS
# or: apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-ben ...  # Debian/Ubuntu

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edit SECRET_KEY etc. for anything beyond local dev

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000`, sign in with a demo account (see
`.env.example`'s `DEMO_USERS`).

## PostgreSQL (verified against a real local instance)

```bash
createdb pramaan
```

Set in `.env`:
```
DATABASE_URL=postgresql+psycopg://<user>@localhost:5432/pramaan
```

Then run the app as above — `init_db()` (called at startup) creates the
schema on a fresh database. This exact sequence (schema creation + a full
authenticated scan cycle) was run against a real local PostgreSQL 16 during
development.

**No Alembic migrations exist yet.** For a schema with no migration history,
`create_all()` is sufficient; the moment this schema needs to evolve in a
deployed environment with real data, Alembic (or an equivalent) becomes
necessary and is not yet wired up. This is a genuine gap for long-lived
production use, not a hidden one.

## Docker (written, not executed here)

```bash
# From the repo root:
docker compose up --build
```

`docker-compose.yml` starts two services: `db` (postgres:16-alpine, with a
healthcheck the `app` service waits on) and `app` (built from the repo-root
`Dockerfile`, which installs Tesseract + all 8 Indic language packs via
`apt-get`, matching what's verified locally via Homebrew). Set `SECRET_KEY`
in your shell environment (or a `.env` file docker-compose reads
automatically) before running this anywhere real — the compose file's
default is explicitly a placeholder.

```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))") docker compose up --build
```

## What's NOT containerized separately

The deck describes separable frontend/backend/worker/database/redis
services. Today: `frontend` is static files served by the same FastAPI
process as the `backend` (no separate service — there's no build step to
containerize independently), there is no `worker` (synchronous pipeline, see
`docs/architecture.md` §4), and there is no `redis` (nothing queues jobs
yet). Only `app` + `db` are real, separate containers. Splitting the frontend
out and adding a worker+Redis service are the next real infrastructure
changes for production, not implemented here.

## Environment reference

See [`backend/.env.example`](../backend/.env.example) for every configuration
value with inline documentation — `DATABASE_URL`, `SECRET_KEY`,
`ACCESS_TOKEN_EXPIRE_MINUTES`, `DEMO_USERS`, `CORS_ALLOW_ORIGINS`,
`MAX_UPLOAD_MB`, `TESSERACT_LANGS`, `CONFIDENCE_THRESHOLD`.

## CI

`.github/workflows/ci.yml` installs Tesseract + Indic language packs +
(best-effort) a Devanagari font on `ubuntu-latest`, installs Python
dependencies, runs `ruff check`, runs the full `pytest` suite, and starts the
real app to confirm `/api/health` and `/api/readiness` respond. Like Docker,
this workflow has not been executed on GitHub's runners from this
environment (no network access to trigger it here) — it's written against
the same verified local toolchain, not run end-to-end yet.
