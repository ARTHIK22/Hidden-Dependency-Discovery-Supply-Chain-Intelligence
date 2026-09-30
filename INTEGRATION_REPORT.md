# Frontend + backend integration report

**Date:** 2026-09-30  
**Overall integration:** **PARTIAL**  
**Frontend:** PARTIAL  
**Backend:** PARTIAL  
**Authentication:** WORKING in API smoke test  
**Database:** local SQLite test database connected; configured PostgreSQL/Neon **NOT VERIFIED**

## Summary

The frontend now uses one environment-configured HTTP client at `frontend/src/services/api/client.ts`, typed feature API modules, bearer-token authentication, protected routes, and real responses for its primary data views. The stale investigation endpoint/body and unsupported WebSocket flow were removed. A direct HTTP integration flow passed against an isolated SQLite database.

This is not a complete product integration. The existing UI contains incomplete/empty component modules, feature gaps in backend APIs, and unsupported UI controls. External research is skipped by the backend workflow. Browser interaction could not be performed because the in-app browser runtime reported no available browsers; this is **NOT VERIFIED** visually. The frontend type check and production build passed.

## Environment

| Setting | Value/status |
|---|---|
| Frontend dev URL | `http://127.0.0.1:5173/` |
| Backend default URL | `http://127.0.0.1:8000/` |
| Frontend API base | `VITE_API_BASE_URL`, default `http://127.0.0.1:8000/api/v1` |
| Integration smoke backend | `http://127.0.0.1:8765/` |
| Database used for smoke test | Isolated SQLite file, removed after verification |
| Configured PostgreSQL/Neon | NOT VERIFIED; no live PostgreSQL/Neon check was performed |
| WebSocket | NOT IMPLEMENTED by backend; frontend investigation page uses HTTP timeline |
| Frontend `.env` | Not overwritten; `.env.example` documents only the safe public API URL |
| Backend secrets | Remain backend-only; no credentials copied into frontend variables |

Backend CORS preflight for `http://127.0.0.1:5173` returned the matching allowed-origin header. `http://localhost:5173` is also included in the backend example/default configuration.

## Integration map

The full module-to-endpoint contract, request/response shapes and limitations are documented in [`docs/integration-map.md`](docs/integration-map.md).

Connected frontend API groups:

- Auth: register, login, current user, profile update.
- Investigations: list, create, get, patch, start, pause, archive, ordered steps.
- Entities: list/search, create, get, patch, alias list/add.
- Relationships: list, get, create, verify.
- Evidence and sources: list/create.
- Graph: neighborhood, shortest path, JSON export.
- Risk analysis: backend structural risk signals.
- Alerts: list/unread filter, mark read.
- Watchlist: list/add/remove.
- Reports and exports: generate stored-data report, graph JSON, relationship CSV.
- System: health and readiness.

The endpoint URLs are relative to `/api/v1`; the frontend makes no direct database requests. `apiClient` adds bearer headers, JSON serialization, a 15-second timeout, JSON/blob decoding, structured HTTP errors and 401 session clearing.

## Features verified

- Frontend TypeScript check: `frontend/node_modules/.bin/tsc.cmd --noEmit` passed.
- Frontend production build: `npm.cmd run build` passed (TypeScript + Vite).
- Backend tests: `backend/.venv/Scripts/python.exe -m pytest app/tests -q` passed, 11 tests.
- Backend Uvicorn started on local port 8765 after Alembic SQLite upgrade.
- HTTP smoke flow passed: register → bearer current-user → create investigation → create entities/source/relationship/evidence → start stored-data workflow → fetch nine ordered steps → generate report → export graph JSON → add watchlist → list scoped evidence.
- Workflow response completed and marks research as `skipped`; it did not claim external lookup.
- CORS preflight from the configured frontend origin succeeded.
- Frontend Vite dev server reached ready state at `127.0.0.1:5173`. Browser visual/navigation testing: NOT VERIFIED because browser runtime listed no available browsers.

## Files modified

Integration updates were limited to the existing frontend architecture plus integration documentation:

- Shared API config/client/interceptors/error mapping and token storage.
- Auth API/store/hook/routes and login/register screens; app routes and header logout.
- Typed feature API functions and request/response types for all available backend route groups.
- Dashboard, investigation list/create/detail, graph, entity/relationship/source lists, evidence, risk, alerts, watchlist and report pages now consume stored backend data.
- Frontend `.env.example`, Vite dev host and integration styles.
- `docs/integration-map.md` and this report.

No backend endpoint behavior was changed in this integration task. The existing backend audit changes remain as they were. The real `frontend/.env` was not modified. No frontend-to-database credentials were added.

## Features requiring attention

| Feature | Problem/cause | Status | Required action |
|---|---|---|---|
| External research and automatic discovery | Backend connector/LLM/agent modules are incomplete; workflow analyzes existing records only | NOT IMPLEMENTED; UI discloses that research is skipped | Implement and verify provider connectors and reviewed evidence ingestion server-side |
| PostgreSQL/Neon persistence | Integration smoke used SQLite; configured hosted database was not reachable/verified | NOT VERIFIED | Configure the backend secret environment and validate migrations and persistence against the intended PostgreSQL instance |
| Browser E2E / visual UI | In-app browser runtime returned an empty browser list | NOT VERIFIED | Run the app in a browser-capable environment and test registration, navigation, data refresh and errors visually |
| WebSocket progress | FastAPI backend has no websocket endpoint | Not available; replaced with HTTP timeline fetch/refresh | Add a supported server progress mechanism only if backend work later requires real-time updates |
| Dashboard totals | Available APIs return bounded arrays without total-count metadata or a dashboard summary route | Displays up to 100 fetched records, labeled as a sample | Add count/summary API only when accurate totals are needed |
| Investigation depth/scope controls | Backend create schema accepts name, target, description, priority only | Visible but non-operative and explicitly described as unsupported | Remove controls or implement a backend contract before enabling them |
| Alert lifecycle | Backend can list and mark read; no create/resolve/acknowledge API | Partial | Add backend lifecycle only when supported by product requirements |
| Secondary screens and reusable widgets | Several unused legacy page/component/hook files in the existing frontend remain empty; connected routes use the new active API-backed pages | Not integrated and not used by active routes | Connect only the screens the product intends to expose, using the documented backend contract |
| Report history | Backend generates a report response but has no report list/read endpoint | Generate/download in current session works; history is not reloadable | Add report retrieval API if persistent report browsing is required |
| Entity/relationship deletion | Backend does not expose these operations | Not offered in connected UI | Implement backend behavior before adding delete controls |
| Pagination and search | Investigation/entity/relationship APIs support limit/offset; source/evidence limits exist. Some views fetch up to the API maximum and filter locally | Partial | Add page controls consistently and avoid interpreting capped lists as total counts |

## Remaining frontend errors

No TypeScript or Vite production build errors remain in the verified build. No backend tests failed. Browser navigation/visual behavior and the configured remote database are unverified, not reported as passing.

## Start instructions

Backend, from `backend/` after configuring `.env` and applying migrations:

```powershell
.\.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, from `frontend/`:

```powershell
npm.cmd run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env` to the safe backend API origin if the API is not at `http://127.0.0.1:8000/api/v1`. Do not place database, JWT-signing, LLM or connector secrets in frontend variables.

## Final assessment

Core HTTP contracts and local persistence flow are connected and build-clean. The complete end-to-end application is **PARTIAL**, not complete: remote PostgreSQL/Neon and browser UI interaction were not verified, and backend external discovery/alerts/background/real-time capabilities are unavailable. The UI now avoids sample “discovery” data in the wired pages and explicitly states where the server performs stored-data-only analysis.
