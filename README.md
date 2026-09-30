# Hidden Dependency Discovery & Supply-Chain Intelligence

Frontend and backend for recording supply-chain investigation requests and inspecting persisted entities, relationships, evidence, risk records, alerts, watchlists, and reports.

## Current implementation scope

- Investigation requests are stored with `queued` status. This repository does not include an automated research agent or background worker, so creating a request does not discover data or advance it automatically.
- PostgreSQL is the configured database. The backend does not substitute SQLite. In development, SQLAlchemy creates missing tables on startup; this is not a migration system.
- Authentication and authorization are not implemented. Do not expose this API to untrusted networks until access control is added.
- Entity, relationship, evidence, and risk views show database records only. Empty tables produce empty states instead of sample intelligence.
- Reports contain counts and risk records read from the database; they are not AI-generated research.

## Backend startup

1. Start a PostgreSQL server and create a database for the project.
2. Copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL` to that PostgreSQL database. Keep the backend `.env` private.
3. From the repository root, install the backend requirements in your Python environment and launch FastAPI:

   ```powershell
   cd backend
   pip install -r requirements.txt
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

The API health endpoint is `http://localhost:8000/api/health`. It reports database connectivity; data routes return `503` when PostgreSQL is unavailable. The interactive API schema is at `http://localhost:8000/docs`.

## Frontend startup

1. Copy `frontend/.env.example` to `frontend/.env` if you need local overrides. The Vite configuration has development defaults for the API and WebSocket URLs.
2. From the repository root:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

The default frontend runs at `http://localhost:5173`. Set `CORS_ORIGINS` in `backend/.env` to the frontend origin if it differs from the defaults. Frontend environment variables are public build-time values; never put credentials or private tokens in them.

## API endpoints

All REST endpoints use the `/api` prefix.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | API and database health |
| `GET` | `/api/dashboard/summary` | Persisted dashboard counts and recent investigations |
| `GET`, `POST` | `/api/investigations` | List and save investigation requests |
| `GET` | `/api/investigations/{id}` | Investigation status and saved record counts |
| `GET` | `/api/entities` | Search/list entities |
| `GET` | `/api/entities/{id}` | Entity and connected relationships |
| `GET` | `/api/search?q=...` | Search stored entities and investigations |
| `GET` | `/api/graph` | Stored entities and relationship edges |
| `GET` | `/api/evidence` | Search/list evidence records |
| `GET` | `/api/evidence/{id}` | Evidence record details |
| `GET` | `/api/risks` | List risk assessments |
| `GET` | `/api/risks/summary` | Risk counts and average score |
| `GET` | `/api/alerts` | List non-dismissed alerts |
| `PATCH` | `/api/alerts/{id}/read` | Mark an alert as read |
| `DELETE` | `/api/alerts/{id}` | Dismiss an alert |
| `GET`, `POST` | `/api/watchlist` | List and add watched entities |
| `DELETE` | `/api/watchlist/{entity_id}` | Remove an entity from the watchlist |
| `GET`, `POST` | `/api/reports` | List reports and generate a persisted-data summary |
| `GET` | `/api/reports/{id}` | Read report contents |
| `GET` | `/api/reports/{id}/download` | Download report text |

The WebSocket status stream is `ws://localhost:8000/ws/investigations/{id}`. It sends the current persisted investigation snapshot; it does not emit agent events because no worker is configured.

## Verification

Verification run on September 30, 2026:

- `npm run build` from `frontend/` passed TypeScript compilation and Vite bundling. Vite emitted a non-blocking warning for the approximately 661 kB minified JavaScript chunk.
- `python -m compileall -q app` from `backend/` passed.
- The backend ASGI smoke check confirmed 20 REST paths in OpenAPI and a successful CORS preflight for `http://localhost:5173`.
- `GET /api/health` returned `200` with status `degraded`; database-backed list endpoints returned `503` because PostgreSQL was unavailable.

The complete database-backed flow could not be verified in this environment: PostgreSQL was unreachable and `psycopg` was missing from the existing virtual environment. The driver is listed in `backend/requirements.txt`; install those requirements and start PostgreSQL before verifying persisted create/read operations.
