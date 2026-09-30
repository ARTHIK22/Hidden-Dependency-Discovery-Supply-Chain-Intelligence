# Implementation Report

**Project:** Hidden Dependency Discovery & Supply-Chain Intelligence
**Updated:** September 30, 2026
**Scope:** Frontend/backend integration and current runtime status

## Executive Summary

The React/TypeScript frontend is connected to a FastAPI backend through a centralized typed Fetch client and configured WebSocket client. The backend exposes REST APIs for persisted investigations, entities, dependency graphs, evidence, risk records, alerts, watchlists, dashboard summaries, and reports. PostgreSQL is the required database; SQLite is not used as a fallback.

Frontend screens now read backend records instead of presenting fabricated supply-chain findings. Empty database results are shown as empty states. Investigation requests can be saved to PostgreSQL with `queued` status, but automated research, entity discovery, and investigation progress workers are not implemented. No agents or AI-generated intelligence are claimed by the application.

## Current Architecture

### Frontend

- React, TypeScript, Vite, and React Router.
- Shared API client in `frontend/src/services/api/client.ts`; API base URL and WebSocket URL are centralized in `frontend/src/config/env.ts`.
- Typed request modules cover investigations, entities/search, evidence, graph relationships, risks, alerts, watchlists, reports, and dashboard summaries.
- Dashboard, investigation history/details, entity explorer, graph, evidence, risk, alerts, watchlist, report, notification, and global-search views use backend responses.
- The interface preserves its existing visual styling while showing loading, error, and empty states for live data.
- Frontend `.env` values are public build-time configuration only. The local `.env` is ignored by Git and `.env.example` supplies non-secret defaults.

### Backend

- FastAPI application and REST API under the `/api` prefix.
- PostgreSQL persistence through SQLAlchemy models and request-scoped database sessions.
- CORS origins are read from backend configuration. The investigation WebSocket is available at `/ws/investigations/{id}` and sends a persisted status snapshot.
- In development, missing tables are created at startup. This is not a database migration system; production schema migrations still need to be introduced and managed.
- Database connection failures are reported by `/api/health`; database-backed routes return `503` when the configured PostgreSQL connection cannot be used.

## Available API Surface

| Area | Implemented operations |
| --- | --- |
| Health | `GET /api/health` |
| Dashboard | `GET /api/dashboard/summary` |
| Investigations | `GET`, `POST /api/investigations`; `GET /api/investigations/{id}` |
| Entities and search | `GET /api/entities`; `GET /api/entities/{id}`; `GET /api/search?q=...` |
| Dependency graph | `GET /api/graph` |
| Evidence | `GET /api/evidence`; `GET /api/evidence/{id}` |
| Risks | `GET /api/risks`; `GET /api/risks/summary` |
| Alerts | `GET /api/alerts`; `PATCH /api/alerts/{id}/read`; `DELETE /api/alerts/{id}` |
| Watchlist | `GET`, `POST /api/watchlist`; `DELETE /api/watchlist/{entity_id}` |
| Reports | `GET`, `POST /api/reports`; `GET /api/reports/{id}`; `GET /api/reports/{id}/download` |
| Investigation status | WebSocket `/ws/investigations/{id}` |

There are 20 REST paths in the generated OpenAPI schema. Read/list views expose persisted data. The current backend does not provide research ingestion endpoints or background discovery jobs that populate entities, relationships, evidence, risks, and alerts automatically. Reports summarize records already stored in PostgreSQL; they are not AI-generated.

## Connected User Flows

1. The dashboard requests persisted counts and recent investigations.
2. Users can submit an investigation goal, scope, and depth. The backend saves the request as queued and the frontend opens its detail page.
3. Investigation detail reads persisted status and record counts. Its WebSocket receives the stored status snapshot; no agent events are produced.
4. Entity, graph, evidence, and risk screens display backend records and their recorded provenance/status fields.
5. Users can add existing entities to the watchlist, remove them, mark alerts read, dismiss alerts, and generate/download data-summary reports.
6. Global search covers stored entities and investigations, matching the current backend search endpoint.

## Security and Scope Limitations

- Authentication and authorization are not implemented. The API must remain in a trusted development environment until access controls are added.
- No research agent, external source connector, entity-resolution worker, evidence verification engine, or risk-calculation worker is present.
- Creating an investigation only stores a queued request. It does not discover data or advance progress.
- Entity, relationship, evidence, risk, and alert records are not populated by an automated pipeline. The frontend does not inject sample intelligence to conceal missing data.
- PostgreSQL is required. Backend `.env` values must remain private; frontend environment variables must never contain credentials or private tokens.
- Development `create_all` creates missing tables but does not update existing schemas. Use migrations before evolving an established database schema.

## Configuration and Startup

1. Start PostgreSQL and create a project database.
2. Copy `backend/.env.example` to `backend/.env`; set `DATABASE_URL` to the PostgreSQL connection string and keep that file private.
3. Install backend requirements and run `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` from `backend/`.
4. Copy `frontend/.env.example` to `frontend/.env` if local overrides are needed. The Vite defaults point to `http://localhost:8000/api` and `ws://localhost:8000/ws`.
5. Run `npm install` and `npm run dev` from `frontend/`.

The backend API schema is available at `http://localhost:8000/docs`. The frontend default origin is `http://localhost:5173`; configure it in backend `CORS_ORIGINS` if it changes.

## Verification Results

- `npm run build`: **passed**. TypeScript compilation and Vite production bundling completed. Vite reported a non-blocking minified JavaScript chunk warning (approximately 661 kB, above the 500 kB advisory threshold).
- `python -m compileall -q app` from `backend/`: **passed**.
- Backend ASGI smoke check: **passed** for route registration and CORS preflight. The generated schema contained 20 REST paths; the configured frontend origin received a successful preflight response.
- Health endpoint: **200**, with database status `unavailable` and overall status `degraded` during this check.
- Database-backed list requests: **503**, as expected while PostgreSQL was unavailable.
- Full database-backed create/read verification: **not completed**. The local PostgreSQL service was unreachable, and `psycopg` was missing from the existing virtual environment. The driver is declared in `backend/requirements.txt`; install the backend requirements and start PostgreSQL before repeating the full flow.

## Recommended Next Work

1. Start PostgreSQL, install backend requirements, then verify investigation create/read and other persisted endpoints against a real database.
2. Add Alembic migrations and a repeatable local database setup.
3. Implement authenticated access before exposing the API beyond trusted local development.
4. Add explicit, source-backed ingestion and a worker system before describing investigation discovery or progress as operational.
5. Add backend integration tests for persistence, validation, CORS, WebSocket snapshots, and failure handling.
6. Consider code splitting the frontend bundle to address the Vite chunk-size advisory.
