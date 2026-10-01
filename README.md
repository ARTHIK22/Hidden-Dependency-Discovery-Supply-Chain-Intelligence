# Hidden Dependency Discovery & Supply-Chain Intelligence

A React/TypeScript and FastAPI application for planning supply-chain investigations, running a bounded research/discovery pipeline, verifying source-backed dependencies, calculating explainable risk, and reviewing user-scoped alerts, watchlists, and reports.

## Demo capabilities and limits

- PostgreSQL-backed records are used by the dashboard and feature pages.
- Account registration, login, current-user lookup, protected API routes, WebSocket bearer authentication, and logout token revocation are implemented.
- The explicit `seed_demo.py` command creates deterministic fictional records so the graph, evidence, risk, alert, watchlist, and report flows have data to show. Every fixture is labeled `DEMO`; it is not verified research.
- Creating an investigation generates and persists a structured plan. A planned investigation can be started; research runs in a bounded in-process background task and stores its progress and results in PostgreSQL.
- No external search provider is configured in this repository. The current fallback is `local_demo`: it generates plan-derived queries, records progress, and returns no sources. It does not create fictional source, evidence, entity, or relationship records.
- Newly created investigations and their research findings are owned by the creating account. The explicitly labeled fictional demo fixture is shared read-only.
- Additive migrations preserve existing tables and records. New investigations are scoped to their creating account; the explicitly fictional unowned demo fixture remains readable across accounts.

## Start the backend

Requirements: Python 3.11 or newer and a PostgreSQL database.

From the repository root in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set `DATABASE_URL` to your PostgreSQL database. Replace `JWT_SECRET_KEY` with a random value of at least 32 bytes. For example:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep `backend/.env` private. Apply the schema and seed the fictional demo scenario:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe seed_demo.py
```

The seed command is safe to rerun. It creates or reuses one named scenario and does not remove existing records. New investigation requests are planned only, regardless of demo mode.

## Planner and investigation plans

The Phase 1 Planner Agent normalizes the submitted goal, attempts deterministic target extraction, and validates its output against the `InvestigationPlan` Pydantic schema. The current `local_demo` mode is rule-based and does not claim to be an LLM. The schema includes target, normalized goal, objective, numeric depth, steps, research questions, expected entity and relationship types, verification requirements, planner mode, and optional target clarification. When the target is ambiguous, the plan retains a `null` target and asks for clarification.

Investigation depth reuses the existing API values: `standard` (direct dependencies), `deep` (upstream dependencies), and `maximum` (deeper tiers and geography). Phase 1 ends at `PLANNED` and remains unchanged.

## Phase 2 research and discovery

The research service consumes the persisted Phase 1 `InvestigationPlan`:

```text
Investigation Plan
  -> Research Orchestrator
  -> Plan-derived queries (bounded by plan depth)
  -> ResearchProvider.search/fetch
  -> Source evidence
  -> Entity extraction
  -> Evidence-backed relationship extraction
  -> PostgreSQL
```

The Research Agent derives its query text from the persisted target, objective, questions, entity/relationship types, steps, and numeric depth. The plan caps the number of steps; it does not recursively expand indefinitely. Source evidence keeps the investigation, URL, title, domain, retrieval time, query, provider, snippet, relevance, and mode. Entity and relationship rows reference the investigation. Relationship rows are created only when an explicit relation phrase is present in source text, and each has at least one linked evidence row. Findings remain `needs_review`; Phase 2 does not verify them.

`ResearchProvider` is an abstract adapter with `search(query)` and `fetch(url, query)` methods. There is no existing external search provider or provider secret configured in this project, so the default adapter is `UnconfiguredResearchProvider`. It reports `research_mode=local_demo`, executes the generated query steps, returns no source records, and clearly says external source discovery is not configured. Provider searches have a bounded timeout (`timeout_seconds`, 30 seconds by default); timeout or provider failure persists `FAILED`. No paid search API, browser automation, or production crawler was added. A real provider can be integrated behind this interface; its results must represent sources actually received. Source URL validation rejects unsafe private/local fetch targets.

The research lifecycle is `PLANNED -> RESEARCHING -> COMPLETED`; `COMPLETED` means discovery ended, not that discoveries were verified. Phase 3 advances eligible investigations through `VERIFYING -> VERIFICATION_COMPLETED`. The authenticated WebSocket at `/ws/investigations/{id}` streams persisted research or verification progress. Graph entities from demo fixtures display a `DEMO DATA` label.

## Phase 3 entity resolution and verification

Phase 3 runs after research completes. `POST /api/investigations/{id}/verify` starts a persisted deterministic background pass; `GET /api/investigations/{id}/verification` reads its state. The pass normalizes names with Unicode case folding, punctuation cleanup, whitespace folding, and legal-suffix removal while retaining every original row and display name. Entity type must match. Same normalized names without corroborating identity context are reported as `POSSIBLE_DUPLICATE`; when normalized names match, explicit aliases/shared identifiers or matching jurisdiction plus similar descriptions can meet the configurable 0.95 automatic resolution threshold. No entity rows are deleted or merged.

Relationship verification evaluates linked evidence records against the relationship endpoints and relation phrase. Demo-only evidence never supports a relationship. A clear positive statement is `SUPPORTED`; positive statements from at least two independent source domains with confidence of at least 0.78 and no contradiction are `VERIFIED`. Positive and negative statements together are `CONFLICTED`; negative evidence alone is `REJECTED`; no direct evidence is `INSUFFICIENT_EVIDENCE`. Source rows and available source dates are preserved. These are deterministic evidence assessments, not claims of certainty.

Evidence strength is calculated as `0.40*relevance + 0.35*directness + 0.10*source_availability + 0.10*recency + 0.05*authority`. Relationship confidence is `clamp(0.55*best_evidence_strength + 0.20*corroboration + 0.15*extraction_confidence + 0.10*consistency - 0.35*conflict_ratio, 0, 1)`. Corroboration saturates at three independent supporting source domains. Unknown relevance, recency, authority, or extraction values use a neutral 0.5 score and are explicitly marked unknown in the persisted breakdown. A missing URL scores zero for source availability. Confidence is an engineering heuristic, not a probability.

Resolution metadata, canonical IDs and aliases, per-evidence classifications, confidence breakdowns, conflict evidence IDs, evaluation timestamps, and progress are persisted in existing JSON metadata plus additive investigation verification state fields. Graph edges distinguish verified, supported, conflicted/rejected, and insufficient-evidence relationships. Entity and relationship inspectors display identity status, evidence counts, sources, confidence, and conflicts.

## Phases 4–6 risk intelligence, alerts, and reports

After verification, `POST /api/investigations/{id}/analyze-risk` calculates a deterministic snapshot from `VERIFIED` non-demo dependency edges and evidence explicitly listed as supporting those edges. Each assessment stores its score on a 0–100 scale, local and propagated contributions, factor status, explanation, evidence IDs, and snapshot ID. Missing criticality, geography, source dates, confidence, or graph context remains `UNKNOWN`; it is not filled with a default. Market-share concentration is calculated only when every share has share-specific source provenance. Supplier-count concentration is labeled as a structural proxy, not as spend share.

The risk model records its factor weights and default level boundaries in each snapshot: MEDIUM at 25, HIGH at 50, CRITICAL at 75. Risk propagates from providers to dependent consumers through verified edges, weighted by relationship confidence and a 0.72 per-hop decay, with a six-hop bound. Dependency direction is normalized for supported relation types; an unknown direction is not guessed. Shared providers, single-source edges, deep paths, and known jurisdiction concentration are recorded as explainable graph patterns.

Risk analysis persists `RISK_ANALYZING` progress before work starts, saves a new snapshot, then advances to `RISK_ANALYZED`. Reports can be generated from that saved state and complete the lifecycle. Deterministic alerts cover threshold crossings, meaningful score increases, newly observed patterns or relationships, stale supporting evidence, verification conflicts, and watchlist threshold crossings. Alert keys prevent duplicate state notifications. Shared demo alert read/dismiss state is stored per user.

Watchlists support entities, relationships, investigations, and risk conditions. Entries belong to the current user; threshold watches record the last observed state and alert when a configured 0–100 limit is crossed. Reports include saved plan, research, source/evidence, entity resolution, relationship verification, graph, risk, alert, unknown, conflict, and lifecycle data. Exports are available as structured JSON, CSV, and plain text. CSV values that could be interpreted as spreadsheet formulas are escaped.

## Phase 7 autonomous monitoring

An owner can enable monitoring after an investigation has completed research and verification. Each run compares a canonical hash of persisted entities, relationships, evidence, verification, risk, watchlist, alert, and investigation settings against the last saved snapshot. Changes and deterministic agent decisions are saved with evidence IDs, a plain-language reason, status, and any follow-up investigation link. Repeated observations are deduplicated.

Supported actions use the existing pipeline: reverify changed relationships, recalculate risk, create existing deterministic alerts, or plan and run a bounded child investigation for a new upstream supplier. Follow-ups inherit the parent's interval, depth limit, and investigation memory and can continue through scheduled child monitors up to the configured depth. Duplicate targets and research queries are suppressed. Unsupported events, verification conflicts, and depth limits are recorded for human review. Autonomous runs do not contact people or take actions outside the application.

Monitoring is opt-in per investigation. Set `MONITORING_SCHEDULER_ENABLED=true` in `backend/.env` to start the single-process scheduler; otherwise runs can be started with the API's **Run now** control. `MONITORING_SCHEDULER_TICK_SECONDS` controls scheduler polling (30–3600 seconds); per-investigation intervals are bounded by `MONITORING_MIN_INTERVAL_MINUTES` and `MONITORING_MAX_INTERVAL_MINUTES` (defaults 15 and 10080). `MONITORING_DEFAULT_INTERVAL_MINUTES` defaults to 60, and `MONITORING_EVIDENCE_FRESHNESS_DAYS` defaults to 180. The scheduler is in-process and is not a distributed job queue, so production multi-worker deployments should run one scheduler instance or move scheduling to a durable worker.

The monitoring panel in Investigation Details shows enabled/status state, last and next check, snapshot version, recorded changes, decision reasons, follow-up links, and lifecycle events. The existing authenticated investigation WebSocket also emits `monitoring_started`, `change_detected`, `agent_decision`, `followup_started`, `followup_completed`, `monitoring_completed`, and `monitoring_failed` events. Phase 7 storage is added by migration `0008_autonomous_monitoring` without removing existing records.

## Phase 8 production hardening and QA

The graph API bounds responses to 500 entities and 1,000 relationships by default (`limit` accepts 25–1,000); entity pages use an `offset` and the UI has previous/next controls. The response reports entity and relationship truncation separately. Graph previews include at most three recent linked evidence records per relationship, while reporting the full evidence count. Entity list responses batch canonical-name and evidence-source lookups. Report generation commits only after report rendering succeeds; failures return a generic error, record an operational lifecycle event, and preserve the prior investigation state. Research, verification, risk, and monitoring starts lock the investigation row to prevent concurrent duplicate starts.

The PostgreSQL mappings use JSON on SQLite and JSONB on PostgreSQL. No new migration was needed for Phase 8; the database is at `0008_autonomous_monitoring`. The existing `0007` and `0008` migrations are additive and forward-only. WebSocket ownership is checked before every snapshot or lifecycle event. The exact test and database snapshot results are in [TEST_REPORT.md](TEST_REPORT.md).

The repository has no separate lint script or external research-provider credentials. `npm run build` runs TypeScript type checking before the production bundle. The default `local_demo` provider produces no source, evidence, entity, or relationship records. E2E uses an isolated SQLite database and deterministic fixture changes; it does not claim live-source discoveries. No PDF exporter is configured; supported report exports are JSON, CSV, and text.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the data model, scoring rules, lifecycle, access boundaries, and migration notes. Demo records keep their fixture labels and displayed sample scores; risk analysis and production alert rules do not treat demo findings as real observations.

Start FastAPI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API health endpoint is [http://localhost:8000/api/health](http://localhost:8000/api/health), and the interactive API schema is [http://localhost:8000/docs](http://localhost:8000/docs).

## Start the frontend

From the repository root in a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and create an account. Frontend environment variables are public build-time settings; do not put passwords, keys, or tokens in `frontend/.env`.

## Authentication and data access

`POST /api/auth/register` and `POST /api/auth/login` return a bearer access token. The frontend stores it locally and sends it to protected `/api` routes. `GET /api/auth/me` resolves the current user. `POST /api/auth/logout` revokes the current token. The investigation WebSocket authenticates with the `hdi` and `bearer.<token>` subprotocols.

Health and the register/login endpoints are public. Dashboard, investigation, entity, graph, evidence, risk, alert, watchlist, and report endpoints require authentication. Investigation, entity, relationship, evidence, graph, verification, risk analysis, alerts, reports, and WebSocket reads are scoped to the investigation owner. Existing rows with no owner are visible only to admins, except the explicitly marked fictional shared demo fixture. Shared demo alert receipts are user-specific; a user's own watchlist entries are private. There is no team/workspace membership model.

## REST endpoints

All REST endpoints use the `/api` prefix.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | API/database status and demo-mode flag |
| `POST` | `/api/auth/register` | Create an account and start a session |
| `POST` | `/api/auth/login` | Start a session |
| `GET` | `/api/auth/me` | Read the authenticated account |
| `POST` | `/api/auth/logout` | Revoke the current access token |
| `GET` | `/api/dashboard/summary` | Persisted dashboard counts and recent investigations |
| `GET`, `POST` | `/api/investigations` | List and save investigation requests |
| `GET` | `/api/investigations/{id}` | Investigation status and saved record counts |
| `GET` | `/api/investigations/{id}/plan` | Retrieve the persisted structured plan |
| `POST` | `/api/investigations/{id}/research` | Start research for a `PLANNED` investigation; returns `202` |
| `GET` | `/api/investigations/{id}/research` | Read persisted research mode, state, progress, and counts |
| `POST` | `/api/investigations/{id}/verify` | Start Phase 3 deterministic verification; returns `202` |
| `GET` | `/api/investigations/{id}/verification` | Read persisted resolution/verification progress and counts |
| `GET` | `/api/investigations/{id}/evidence` | List source evidence for one investigation |
| `GET` | `/api/investigations/{id}/entities` | List entities discovered for one investigation |
| `GET` | `/api/investigations/{id}/relationships` | List relationships discovered for one investigation |
| `GET` | `/api/entities` | Search/list entities |
| `GET` | `/api/entities/{id}` | Entity and connected relationships |
| `GET` | `/api/search?q=...` | Search saved entities and investigations |
| `GET` | `/api/graph` | Persisted graph nodes and relationship edges |
| `GET` | `/api/evidence` | Search/list evidence records |
| `GET` | `/api/evidence/{id}` | Evidence record details |
| `GET` | `/api/risks` | Persisted risk assessments; scores are returned on a 0–100 scale |
| `GET` | `/api/risks/summary` | Risk counts and average score |
| `POST` | `/api/investigations/{id}/analyze-risk` | Start deterministic analysis after completed verification; returns `202` |
| `GET` | `/api/investigations/{id}/risk-analysis` | Read persisted analysis status and progress |
| `GET` | `/api/investigations/{id}/risks` | List the latest investigation risk snapshot |
| `GET` | `/api/investigations/{id}/risk-summary` | Read snapshot summary, thresholds, unknown counts, and relationship statuses |
| `POST`, `DELETE` | `/api/investigations/{id}/monitor` | Enable or disable monitoring for a completed, owned investigation |
| `POST` | `/api/investigations/{id}/monitor/run` | Start a manual monitoring run; returns `202` |
| `GET` | `/api/investigations/{id}/monitoring` | Read status, interval, last/next check, and latest snapshot version |
| `GET` | `/api/investigations/{id}/changes` | Read deduplicated detected changes |
| `GET` | `/api/investigations/{id}/agent-decisions` | Read persisted decisions, reasons, results, and follow-up links |
| `GET` | `/api/entities/{id}/risk` | Read latest entity risk assessment |
| `GET` | `/api/relationships/{id}/risk` | Read latest relationship risk assessment |
| `GET` | `/api/alerts` | List visible non-dismissed alerts; supports `unread_only`, `limit`, and `offset` |
| `GET` | `/api/alerts/unread-count` | Count unread alerts for the current user |
| `PATCH` | `/api/alerts/read-all` | Mark visible alerts read for the current user |
| `PATCH` | `/api/alerts/{id}/read` | Mark an alert as read |
| `PATCH`, `DELETE` | `/api/alerts/{id}/dismiss` | Dismiss an alert for the current user |
| `GET`, `POST` | `/api/watchlist` | List and add an entity, relationship, investigation, or risk condition |
| `DELETE` | `/api/watchlist/items/{id}` | Remove an owned watchlist entry |
| `DELETE` | `/api/watchlist/{entity_id}` | Remove an entity from the watchlist |
| `GET`, `POST` | `/api/reports` | List reports and generate a saved-data summary |
| `GET` | `/api/reports/{id}` | Read report contents |
| `GET` | `/api/reports/{id}/download` | Download report text |
| `GET` | `/api/reports/{id}/export?format=json\|csv\|txt` | Download JSON, CSV, or text |

The WebSocket status stream is `ws://localhost:8000/ws/investigations/{id}`. It requires the existing `hdi` and `bearer.<token>` subprotocols and sends persisted `snapshot`, research, verification, risk, and monitoring lifecycle events. Verification snapshots include entity-resolution and relationship-status counters. Each event checks investigation ownership; the explicitly fictional shared demo fixture remains available to authenticated users.

## Tests and builds

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest app/tests -q
.\.venv\Scripts\python.exe -m compileall -q app database seed_demo.py
.\.venv\Scripts\python.exe -m alembic check
```

From `frontend/`:

```powershell
npm run build
npm run test:e2e
```

The Playwright command starts the API and Vite servers against an isolated temporary SQLite database. It uses installed Chrome when available; install Playwright Chromium with `npx playwright install chromium` if Chrome is not installed. End-to-end checks use a uniquely marked temporary account and scenario. Backend tests use isolated SQLite fixtures and do not depend on external APIs.

The browser flow covers the Acme plan, local demo research, verification, risk, monitoring change detection and follow-up, reports and downloads, and login persistence. It also checks dashboard layout at tablet and mobile widths. Separate backend tests confirm the NVIDIA target is isolated from an Acme investigation and that “Investigate battery supply chain” retains a null target with a clarification request.
