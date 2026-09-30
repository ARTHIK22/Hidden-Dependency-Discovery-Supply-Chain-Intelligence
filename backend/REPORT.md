# Backend audit report

**Project:** Hidden Dependency Discovery / Supply Chain Intelligence  
**Audit date:** 2026-09-30  
**Scope:** `backend/` only. No frontend files were changed.

## 1. Executive summary

The existing FastAPI backend now starts locally, core API flows work against SQLite, and 11 integration/unit tests pass. The API has usable authentication, investigation records and a bounded workflow over stored evidence, entity/relationship records, graph analysis, risk heuristics, watchlists, reports and exports.

**Final recommendation: NOT READY for full frontend integration as a complete supply-chain discovery product.** A limited integration can use the implemented API, but real research is not performed: several existing agent, LLM, worker and connector modules are empty or incomplete. The workflow labels research as skipped and does not persist extraction candidates as facts. PostgreSQL was not available for verification. These limitations are not represented as successful discovery.

## 2. Audit scope and method

Reviewed backend Python modules, API routers, models, schemas, services, engines, configuration, requirements, Alembic setup and tests. Ran the test suite, Python compilation, SQLite Alembic upgrade/current/heads checks, and a live Uvicorn smoke test. Fixed issues found in core API and workflow paths and reran tests.

## 3. Architecture and data flow

The preserved structure remains `app/`, `orchestration/`, `extraction/`, `resolution/`, `verification/`, `graph/`, `risk_engine/`, `connectors/`, `llm/`, `workers/`, and `database/migrations/`. The implemented API path generally follows router → Pydantic schema → service or database session → SQLAlchemy model. Graph and risk modules are called by services and the local investigation workflow.

The full research chain is not connected end to end. In particular, the orchestration workflow does not invoke external connectors or LLM agents.

## 4. Configuration and environment

Settings are loaded through Pydantic Settings. CORS accepts either a JSON array string or comma-separated origins. Production settings reject a short JWT secret and debug mode. Database, Redis, CORS and signing settings remain environment-configurable. No secret values are included in this report.

## 5. Application startup and routes

Verified an actual Uvicorn process on `127.0.0.1:8765`. `GET /`, `GET /api/v1/health` and `GET /docs` returned HTTP 200. The requested port 8000 was already occupied, so the isolated smoke test used 8765; the existing service on 8000 also returned the expected API root. Routers register under `/api/v1`; exception handlers and request logging middleware load. Redis being unavailable did not prevent startup or health response.

## 6. Database models and constraints

The model registry includes users, organizations, investigations, investigation steps, entities, aliases, relationships, evidence, sources, locations, facilities, risks, risk events, alerts, watchlists, reports and audit logs. Constraints cover selected confidence/score ranges and unique relationships, aliases and watchlist entries. SQLite creates the full metadata schema successfully. PostgreSQL connectivity and production behavior were not exercised.

## 7. Alembic and migrations

`alembic upgrade head`, `alembic current` and `alembic heads` succeeded using an isolated SQLite database; the revision reported as `0001_initial_schema (head)`. Alembic imports `Base.metadata` after loading the model package.

The initial migration currently calls `Base.metadata.create_all()` rather than containing a frozen schema snapshot. It bootstraps a fresh database, but is not a safe substitute for versioned, explicit schema-change migrations on an already deployed database. `alembic check` against SQLite reports UUID type differences because SQLite reflects PostgreSQL UUID columns differently; no PostgreSQL server was available to confirm autogeneration there.

## 8. Authentication

Registration, login, current-user lookup, duplicate credentials and invalid-password paths are covered. Passwords are hashed with bcrypt; bearer tokens are JWTs with expiration. Password hashing was changed from an incompatible Passlib/bcrypt combination to direct bcrypt calls.

## 9. User permissions and investigation privacy

Investigation ownership is checked for read, update, start, timeline, report and archive operations. Evidence must belong to an investigation, and evidence creation/listing plus verification evidence lookup are scoped to the caller’s investigation (admins may access across owners). A regression test confirms another user receives 404 for a private investigation and cannot attach evidence to it.

Organization membership and shared-organization roles are not implemented. Entity and relationship catalogs are shared across authenticated users.

## 10. Investigation records and lifecycle

Create, list, get, patch, start, pause and archive endpoints are present. Legal status transitions are checked for patches. Starting/resuming runs the local workflow synchronously. The workflow writes an ordered timeline and generated JSON report. The pause endpoint cannot interrupt an active synchronous request; durable background execution is not implemented.

## 11. Investigation workflow

The nine recorded stages are planning, research, extraction, resolution, verification, graph, risk, recommendation and report. Research is explicitly `skipped` with external access marked false. Extraction only searches recorded evidence for known entity names/aliases. Resolution reports matches but never auto-merges. Verification evaluates stored, caller-visible evidence and does not claim unsupported facts. Graph/risk/recommendation/report stages operate on recorded database content.

This is a useful local analysis workflow, not external hidden-dependency discovery. Extracted candidates are stored in step output only and are not promoted to relationships.

## 12. Entity and alias system

Entity creation, listing/search, aliases and alias-based search are exercised. Canonicalization normalizes names and similarity helpers support candidate comparison. The current implementation does not provide a complete entity review/merge workflow or broad entity-type-specific validation.

## 13. Relationship system

Relationships can be recorded with type, confidence, verification status and metadata. Duplicate directed relationship triples are rejected. Verification requires evidence and evaluates the evidence/source records rather than blindly marking a claim verified. Relationship records are shared catalog data; no per-organization ownership model exists.

## 14. Evidence and source records

Evidence stores content, content hash, source/relationship/entity references, confidence, URL and publication/collection metadata. Sources are separate records with reliability metadata. Evidence/report/verification paths use stored values; URLs are not fetched or independently validated. Contradiction detection is not wired into a persistent review workflow.

## 15. Connectors, research and LLMs

The connector and provider directories exist, but zero-byte modules remain in `connectors/` and `llm/`, including connector registry/base and provider/base/OpenAI/Gemini/embeddings/prompt/response modules. The workflow does not invoke external search, registries, company sources or LLMs. Missing keys therefore do not crash startup, but the intended research capability is not available.

## 16. Agents and workers

Agent and worker directories contain zero-byte modules, including the shared agent context/registry/result/base and the investigation, research, extraction, verification, risk, report and export workers. They are not used by the synchronous workflow. No background queue or scheduling system is configured.

## 17. Graph and dependency analysis

Graph construction, traversal, path finding, serialization and dependency analyzers are implemented and unit-tested. The graph API returns stored relationships; direct and shared supplier signals are exercised. Directional semantics vary by relationship type and should be confirmed before treating every edge as a supply dependency.

## 18. Risk analysis

Risk modules calculate explainable structural signals such as common dependency, supplier concentration, single point of failure and geographic concentration where data supports it. The API states that analysis uses recorded relationships and no external risk feeds. Scores are heuristics, not threat-intelligence measurements. Risk persistence and end-to-end risk propagation are not fully integrated into investigations.

## 19. Alerts and watchlists

Watchlist add/list/remove is covered and entries are user-scoped. Alert listing and marking read exist; alert queries are scoped through their investigation owner. There is no complete alert creation, acknowledgement/resolution lifecycle, or demonstrated automatic connection from risk/watchlist changes to alert generation. Alert functionality is therefore partial.

## 20. Reports and exports

Reports are generated from stored investigation data and include the investigation target, linked entities/relationships, evidence, sources, persisted risks and confidence when available. The workflow report appends its calculated risk signals and recommendations. JSON report generation and graph JSON/relationship CSV exports are tested. PDF export is not implemented or claimed.

## 21. API endpoint groups

The registered groups include `/api/v1/health`, `/auth`, `/users`, `/entities`, `/relationships`, `/investigations`, `/graph`, `/evidence`, `/sources`, `/risks`, `/alerts`, `/watchlists`, `/reports` and `/exports`. Investigation timeline is available at `/api/v1/investigations/{investigation_id}/steps`.

## 22. Tests and verification results

- `python -m pytest app/tests -q`: **11 passed**, 2 dependency deprecation warnings.
- `python -m compileall -q app database/migrations graph resolution risk_engine extraction verification orchestration connectors llm workers utils`: **passed**.
- SQLite `alembic upgrade head`, `current`, `heads`: **passed**.
- Uvicorn startup and live root, health and docs requests: **passed**.
- SQLite health showed database connected; Redis unavailable. PostgreSQL, real external connectors, LLM calls, and background execution were not tested.

## 23. Defects fixed during audit

- Fixed CSV export response import and relationship verification response schema issues.
- Fixed Alembic logging configuration and model registration for migration startup.
- Replaced incompatible password hashing integration with supported bcrypt calls.
- Corrected health-test database setup and SQLite in-memory pooling.
- Connected investigation start/resume to the bounded workflow, added ordered timeline retrieval, and ensured repeat runs do not reuse step sequence numbers.
- Added target/source/entity/confidence fields to stored report summaries.
- Enforced evidence ownership by investigation and scoped evidence-based verification and alert reads to investigation owners.
- Updated tests to assert truthful skipped research status and private investigation access.

## 24. Known limitations and final recommendation

The backend is **NOT READY** for full frontend integration as the requested complete product because external research/connectors, LLM providers, shared agents/workers, persistent candidate review/merge, full alert lifecycle, organization permissions and production PostgreSQL migrations remain incomplete or unverified. Existing empty modules compile but provide no functionality. The local API can support a limited integration around stored data and synchronous analysis, provided the UI communicates those limits.

## 25. Run instructions

From `backend/`, install `requirements.txt`, configure `.env` with a reachable PostgreSQL database and a strong `JWT_SECRET_KEY`, then run:

```powershell
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `/docs` for the API schema. Redis is optional for the currently implemented request paths. Do not treat the SQLite audit database as a production migration validation.

## 26. Final checklist

| Area | Result |
|---|---|
| Application startup and API routing | PASS (local smoke test) |
| SQLite connection and health | PASS |
| PostgreSQL connection | NOT VERIFIED |
| Alembic upgrade/current/heads | PASS (SQLite bootstrap) |
| Authentication | PASS (covered paths) |
| Investigation workflow and timeline | PASS (stored-data only; research skipped) |
| Entity/relationship/evidence/source core | PASS (covered paths) |
| Graph and structural risk | PASS (limited heuristics) |
| Alerts | PARTIAL |
| Watchlists | PASS (CRUD paths) |
| Reports/JSON/CSV exports | PASS (covered formats) |
| External research, LLMs, background workers | NOT IMPLEMENTED |
| Automated tests | PASS (11 tests; not exhaustive) |
| Overall | **NOT READY** |
