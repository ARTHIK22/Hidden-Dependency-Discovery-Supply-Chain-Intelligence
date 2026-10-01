# Product Completion and QA Report — Phases 1–8

Run date: 2026-10-02

## Phase 4 result — risk intelligence

Risk analysis scores persisted verified non-demo edges only, saves an explainable snapshot, preserves unknown inputs, and bounds graph propagation. The full backend suite passes, including scoring bounds, evidence provenance, critical-dependency patterns, and saved snapshots.

## Phase 5 result — alerts and watchlists

Alert generation and threshold evaluation are deterministic and deduplicated. Watchlist entries cover entities, relationships, investigations, and risk conditions; user-owned entries and shared-demo read receipts remain scoped. Backend integration tests pass for alert receipts, target types, ownership, and watchlist transitions.

## Phase 6 result — reports and exports

Reports include persisted evidence, entities, relationships, verification, risk, alerts, unknowns, conflicts, and lifecycle events. JSON, CSV, and text exports are supported; CSV formula-like values are escaped. A report-render failure regression verifies that the previous investigation state and data survive and that the API returns a generic error.

## Phase 7 result — autonomous monitoring

Phase 7 adds opt-in continuous monitoring backed by persisted configuration, run and snapshot records, deduplicated change/decision histories, graph versioning, autonomous memory, bounded follow-up investigations, owner-scoped APIs, authenticated WebSocket events, a monitoring panel, and an optional scheduler. Runs reuse the existing planner, research, verification, risk, and alert services. Child monitors inherit the configured interval and depth limit. Migration `0008_autonomous_monitoring` is additive; no existing records are dropped or rewritten by its model changes.

The scheduler remains disabled by default. Manual monitoring is available without starting the scheduler. Scheduling is in-process and intended for one scheduler instance; production multi-worker deployments need durable coordination. The default research provider remains unconfigured, so no external-source discoveries are claimed.

The feature set includes deterministic verified-graph scoring, evidence-backed risk factors, alerts and user-scoped watchlists, report exports, and opt-in monitoring with bounded autonomous follow-ups. The default provider remains unconfigured; no real-source findings are claimed.

## Phase 8 result — production hardening and final QA

**Final gates:** backend **PASS — 55 tests passed, 0 failed** (2 dependency deprecation warnings); Python compilation **PASS**; Alembic upgrade **PASS — database at `0008_autonomous_monitoring`**; Alembic check **PASS — no new upgrade operations**; frontend production build **PASS** (TypeScript and Vite; 702.43 kB minified JS, 219.31 kB gzip); Playwright **PASS — 1 end-to-end flow passed in 25.5 seconds**. The Windows server shutdown printed a benign Proactor connection-reset diagnostic. One earlier Playwright selector did not match the edge's accessible name; the flow now clicks the rendered SVG path and passes. No separate lint script is configured.

The browser flow covers registration/login, fictional demo pages, Acme investigation planning, explicitly empty `local_demo` research, verification, unknown-risk analysis, deterministic monitoring change and follow-up, report text/JSON/CSV downloads, logout/login persistence, and dashboard layout at 1024×768, 768×1024, and 390×844. Backend tests separately verify NVIDIA and Acme plans remain distinct, and the ambiguous battery goal keeps a null target with clarification. These deterministic tests do not exercise external-source discovery. No PDF export is configured.

**Security:** missing, malformed, expired, and revoked tokens are rejected. Passwords use bcrypt; JWT secrets remain server-side; owner-scoped APIs and WebSockets are tested, including ownership transfer while connected; CORS uses configured origins; output errors are generic; application queries use SQLAlchemy parameters. The app uses bearer headers rather than cookie sessions, so conventional CSRF is not applicable; React renders text without raw HTML injection. Rate limiting is not implemented, so public deployments need a shared login/register limiter. No separate team/workspace membership model exists.

**Data integrity:** live PostgreSQL revision `0008_autonomous_monitoring`; `alembic upgrade head` completed and `alembic check` reported no drift. Before/after Phase 8 row counts were unchanged: users 5, investigations 3, entities 21, relationships 21, evidence 20, risks 6, alerts 4, watchlist entries 4, reports 0. Alert receipts and all five monitoring/agent tables are present and each has 0 rows. Sixteen reference, ownership, cross-investigation, confidence, and risk-range checks returned 0. Six duplicate checks for case-insensitive account emails, evidence source identity, alert dedupe keys, watchlist targets, monitoring changes, and agent decisions also returned 0. Observed statuses were `completed` (2) and `queued` (1) for investigations; `verified` (9) and `demo_unverified` (12) for relationships; `verified` (8) and `demo_unverified` (12) for evidence; and the expected `fraction` legacy risk scale (6) and `watching` watchlist state (4). Monitoring and agent tables were empty.

**Hardening fixes:** PostgreSQL JSONB mappings now match Alembic metadata; report completion commits only after rendering, and failure preserves the last valid state; row locks prevent concurrent duplicate starts; WebSocket access is revalidated before each send; graph responses are entity-paginated and bounded (500 entities and 1,000 relationships by default, request limit up to 1,000 entities) and include at most three evidence previews per relationship; entity-list enrichment batches canonical and evidence lookups to avoid per-row queries.

**Performance and remaining limits:** graph payloads and research depth are bounded; entity-list access is paginated and enrichment is batched. There is no external provider configured, so fresh investigations can complete with zero source-backed results. Background work and the optional scheduler are in-process and not durable across restarts or coordinated across workers. Risk thresholds are heuristics. No automated axe or color-contrast audit is configured. The production JS bundle is above Vite's 500 kB advisory.

**Files changed in the hardening pass:** `backend/app/models/base.py`, JSON model mappings, graph/entity/investigation APIs, investigation start services, report service and route, regression tests under `backend/app/tests`, graph API/client UI, Playwright E2E, `README.md`, `ARCHITECTURE.md`, and this report. No new migration was required; revisions `0007` and `0008` are already applied. No commit or push was made.

The E2E fixture uses a temporary SQLite database and deterministic fixture changes. It validates the monitoring decision and bounded follow-up pipeline; because `local_demo` returns no source records, the run does not claim real supplier discovery or a newly verified lithium dependency. The configured live PostgreSQL counts above confirm existing records were preserved.

Monitoring unit and integration coverage includes enable/disable and interval behavior, manual/scheduled runs, no-change `NO_ACTION`, graph/evidence/risk changes, stale evidence and conflicts, alerts, follow-up research with inherited memory and schedule, query/target deduplication, depth limits, owner authorization, and WebSocket event access.

## 1. Phase 3 implementation summary (historical)

Phase 3 added deterministic entity resolution, alias and duplicate-candidate handling, evidence aggregation, relationship verification, confidence scoring, contradiction preservation, database-backed progress, authenticated APIs, WebSocket updates, and frontend inspectors. Original entity and relationship rows remain intact. At the end of Phase 3, the terminal status was `VERIFICATION_COMPLETED`; Phase 4 now advances eligible investigations through risk analysis.

## 2. Phase 1 compatibility

The planner and persisted investigation plan remain unchanged. Verification requires a saved plan and completed research. Existing `PLANNED` investigations still use the Phase 1 plan flow, and cannot start verification directly.

## 3. Phase 2 compatibility

Research still finishes at `COMPLETED` and preserves its existing evidence, entity, relationship, and progress records. Verification accepts the persisted `COMPLETED` research state (and compatible `RESEARCH_COMPLETED` state). Local demo research creates no findings; its empty result can be verified and completes with zero counts. Phase 2 test fixtures now reuse the investigation owner account to reflect the enforced ownership scope.

## 4. Files changed

- Backend: `app/agents/entity_resolution.py`, `app/agents/verification.py`, `app/services/verification_service.py`, `app/api/access.py`.
- Backend integration: investigation model and service, investigation/entity/evidence/graph routes, and investigation/entity/relationship/evidence schemas; new verification schema.
- Database: `database/migrations/versions/0006_verification_ownership.py`.
- Backend tests: new `app/tests/test_verification.py`; owner-corrected Phase 2 research test setup.
- Frontend: API types and investigation API, Investigation Details, Graph, Entity Explorer, Evidence drawer, and related styles.
- Browser flow: `frontend/e2e/demo-flow.spec.ts`.
- Docs: `README.md` and this report.

## 5. Migration details

Revision `0006_verification_ownership` follows `0005_research_discovery`. It additively adds `verification_mode`, JSON `verification_progress`, nullable `owner_id`, its `users` foreign key, and an index. Resolution and relationship verification details use existing JSON metadata; no entity, relationship, or evidence rows are dropped or rewritten. PostgreSQL `alembic upgrade head` applied successfully, followed by `alembic check` with no new operations detected. Historical ownerless records remain preserved and are admin-only, except for the explicitly fictional shared demo fixture.

## 6. Entity Resolution architecture

`resolve_entities` normalizes Unicode/case, punctuation, whitespace, and trailing legal suffixes without changing display names. Candidate pairs require matching entity types. Explicit aliases or shared identifiers score 0.99; matching normalized names without identity context remain `POSSIBLE_DUPLICATE` at 0.88. Matching normalized names plus matching jurisdiction and similar descriptions can score 0.96. The automatic resolution threshold is 0.95 and can be passed to the resolver. Canonical selection prefers the plan target, evidence provenance, populated descriptions, then deterministic name/time/ID ordering. No database rows or relationship endpoints are destructively merged; canonical IDs and aliases are recorded in entity metadata.

## 7. Relationship Verification architecture

`verification_service.py` loads one owned investigation’s entities, relationships, and evidence; resolves entities; groups relationships by resolved endpoint IDs and type; aggregates their linked evidence; and persists one assessment across each candidate group. The graph then displays a single edge per canonical relationship while preserving every source relationship row. It records resolution and verification modes, status, confidence, candidate IDs, supporting/conflicting evidence IDs, reasons, score details, source dates, and evaluation time. Background work uses a separate database session and records `FAILED` with a generic error if processing fails.

## 8. Evidence verification logic

Evidence supports or contradicts a relationship only when one statement contains both entity names (or recorded aliases) and a recognized relationship phrase. Explicit negation/cessation language marks a contradiction. Demo-only evidence is never supporting evidence. Unrelated text remains unrelated; no direct evidence results in `INSUFFICIENT_EVIDENCE`. Independent corroboration counts unique source domains, using the source URL host or persisted source-domain metadata. Unknown quality properties are marked unknown rather than inferred from publisher names.

## 9. Confidence scoring formula

Evidence strength:

`0.40 × relevance + 0.35 × directness + 0.10 × source_availability + 0.10 × recency + 0.05 × authority`

Relationship confidence:

`clamp(0.55 × best_evidence_strength + 0.20 × corroboration + 0.15 × extraction_confidence + 0.10 × consistency − 0.35 × conflict_ratio, 0, 1)`

Corroboration is `min(1, (independent_supporting_domains − 1) / 2)`. Unknown relevance, recency, authority, and extraction confidence use a neutral 0.5 term and carry an `*_known` flag; a missing source URL scores zero for availability. These heuristic scores are not probabilities. `VERIFIED` requires supporting evidence, at least two independent domains, confidence of at least 0.78, and no conflict.

## 10. Conflict handling

Positive and contradictory records produce `CONFLICTED`; both evidence sets and their source records are retained. Contradictory evidence alone produces `REJECTED`. A mixed statement can be recorded in both evidence ID sets. Conflicts are not resolved by choosing a preferred source. Per-evidence classifications and conflict ratios remain visible to the API and graph inspector.

## 11. API changes

- `POST /api/investigations/{id}/verify` starts verification and returns `202` with persisted state.
- `GET /api/investigations/{id}/verification` returns verification mode, progress, counts, status, and safe error state.
- Existing investigation entity/relationship/evidence endpoints now expose resolution metadata, verification details, source names, evidence counts, and conflict indicators.
- The graph response includes resolution state, evidence items, source counts, verification status/confidence, conflict evidence counts, and verification time.

## 12. WebSocket changes

`/ws/investigations/{id}` emits `verification_progress` snapshots while verifying and after completion. Each snapshot carries persisted entity and relationship counters and verification mode. Authentication, origin checks, and investigation ownership are validated before streaming; the socket closes on terminal status.

## 13. Frontend changes

Investigation Details shows **Start Verification**, progress, canonical/alias/ambiguous entity counts, relationship status counts, and the “risk analysis has not started” completion message. A small polling fallback refreshes a very short verification run if it completes between WebSocket snapshots. Entity Explorer shows canonical identity, aliases, resolution confidence, evidence count, and sources. The graph adds a status legend and status-specific edge styling; its inspectors show relationship endpoints, confidence, sources, evidence text, conflicts, and verification time. The evidence drawer shows source title/URL, retrieved and published dates, evidence classification, and conflicting evidence IDs.

## 14. Security/authentication

Every Phase 3 REST route inherits bearer authentication. Investigation, entity, evidence, graph, and WebSocket data are scoped to the investigation owner. New investigations record their creator. Existing ownerless non-demo data is accessible to admins only because no trustworthy historical owner mapping exists; the clearly labeled fictional demo fixture remains shared. No workspace membership model exists. WebSocket uses the existing bearer subprotocol and origin validation.

## Historical Phase 3 validation commands

- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe -m compileall -q app database seed_demo.py e2e_server.py`
- `.venv\Scripts\python.exe -m alembic upgrade head`
- `.venv\Scripts\python.exe -m alembic check`
- `npm.cmd run build`
- `npm.cmd run test:e2e`

## Historical Phase 3 test results

- Backend: **PASS — 31 passed**, with two dependency deprecation warnings.
- Compileall: **PASS**.
- PostgreSQL migration: **PASS — revision 0006 applied**.
- Alembic check: **PASS — no schema drift detected**.
- Frontend build: **PASS**. Vite reported the existing-style advisory that the minified JS chunk is larger than 500 kB (683.58 kB).
- Playwright: **PASS — 1 complete browser flow passed**. Windows emitted benign Proactor connection-reset diagnostics during server shutdown; the flow’s API and page error checks were empty.

## Historical Phase 3 end-to-end results

The in-app browser smoke pass could not run because the browser runtime reported no available browser. The Playwright browser flow exercised the full path against its isolated temporary SQLite database: registration/login, existing demo pages, plan creation, local demo research, Start Verification, empty-result completion, refresh persistence, entity inspection, graph node and relationship inspectors, evidence drawer, reports, existing risk/alert/watchlist pages, logout, and login. No live search provider is configured, so no external-source verification run was possible. The configured PostgreSQL migration was tested separately.

## 18. Example entity resolution

`Apple Inc.` and `Apple Incorporated` normalize to `apple`; with no supporting context they remain possible duplicates and are not automatically merged. If a source record explicitly lists `Apple Inc.` as an alias of the other record (or both records share a strong identifier), matching `COMPANY` entities resolve to one deterministic canonical ID. `Apple` as `COMPANY` cannot merge with `Apple` as `PRODUCT`.

## 19. Example verified relationship

For “Supplier B supplies Acme Electronics,” two direct source statements from distinct domains, 0.8 extraction/relevance values, available URLs, and unknown dates/authority yield approximately 0.7848 confidence under the documented formula. The relationship becomes `VERIFIED` because it exceeds 0.78 with two independent sources and no contradiction. Three independent supporting sources increase the corroboration term and confidence.

## 20. Example conflicting relationship

If one source says “Supplier B supplies Acme Electronics” and another says “Supplier B no longer supplies Acme Electronics,” the relationship is `CONFLICTED`. Both evidence IDs, URLs, source dates when present, and classifications remain persisted and visible. The engine does not decide which statement is current unless source dates and evidence explicitly support that assessment; it does not infer that from age alone.

## 21. Known limitations

- No live research provider or LLM is configured; verification is deterministic and explicitly labeled.
- Relation-language and negation detection use a bounded phrase set and can miss paraphrases or nuanced clauses. Confidence thresholds require future calibration against reviewed data.
- Independent sources are counted by domain; syndicated content on different domains may not be truly independent.
- Existing ownerless non-demo records need an administrator to assign trustworthy owners before regular users can access them. There is no team/workspace sharing model.
- Background jobs are in-process and are not durable across service restarts.
- Risk factors and alert thresholds are deterministic engineering heuristics. They need calibration against reviewed supply-chain data; the unconfigured provider means no real-world risk conclusions are available from a newly created empty investigation.
- In-process background jobs are not durable across a server restart.

## Phase 4–6 completion scope

Risk analysis uses persisted `VERIFIED` non-demo relationships and verifier-selected supporting evidence; non-verified statuses stay visible in summaries and reports. Scores, factors, propagated contributions, graph patterns, alert reasons, report JSON, and lifecycle events are persisted. User access is scoped to investigation ownership, with per-user watchlist entries and shared-demo alert receipts. Revision `0007_risk_alerts_reports` is additive; its live PostgreSQL upgrade and data-integrity checks completed and are summarized in Phase 8 results above.
