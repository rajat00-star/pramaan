# PraMaan Deployment

## Honesty note up front

`docker compose up -d --build` has been run and verified directly in this
project: both containers (`app`, `db`) reach a healthy state, the app
container's PostgreSQL connection is real (not SQLite), and a full
authenticated cycle — login, image upload, real OCR/extraction/rule-engine
verdict, dashboard aggregation, review correction, audit trail, replay — was
exercised end-to-end against `http://127.0.0.1:8000` while it ran. `/docs`
(Swagger) and the existing web app were both confirmed working against the
Dockerized instance, not just the native dev server.

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

## Docker (verified)

```bash
# From the repo root:
docker compose up -d --build
docker compose ps      # both services should show healthy/running
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

## Mobile app

The React Native/Expo mobile app (`frontend/mobile/`) is a separate client,
not something this Docker setup builds or serves — it connects to whichever
backend URL you configure (Docker or native dev server, see
[`docs/mobile.md`](mobile.md)). No mobile-specific server-side deployment
step exists; `EXPO_PUBLIC_API_URL` in `frontend/mobile/.env` is the only
thing that needs to point at wherever the backend above is actually running.

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
