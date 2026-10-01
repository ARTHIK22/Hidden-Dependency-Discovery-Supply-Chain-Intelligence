# Architecture and operating model

## Investigation lifecycle

| Stage | State transition | Persisted output |
| --- | --- | --- |
| Plan | create → `PLANNED` | Validated plan and bounded research steps |
| Research | `PLANNED` → `RESEARCHING` → `COMPLETED` | Provider results, sources, evidence, extracted entities and relationships |
| Verify | `COMPLETED` → `VERIFYING` → `VERIFICATION_COMPLETED` | Entity resolution, evidence classifications, confidence, and conflicts |
| Risk | `VERIFICATION_COMPLETED` → `RISK_ANALYZING` → `RISK_ANALYZED` | Immutable risk snapshot, factors, graph patterns, alerts, and progress |
| Report | `RISK_ANALYZED` → `COMPLETED` | Structured report and text/JSON/CSV exports |
| Monitor | stable verified investigation → `MONITORING_ENABLED` ↔ `MONITORING_RUNNING` → `MONITORING_COMPLETED` | Monitoring config, run, canonical state snapshot, deduplicated changes, decisions, and follow-up links |

Research and verification use bounded in-process background work. Risk work also runs in-process after the API commits `RISK_ANALYZING`. This makes progress visible and recoverable from database state, but queued jobs are not durable across a server restart. A production deployment should move these jobs to a durable worker queue.

The current research provider is deliberately unconfigured and creates no source or finding rows. The deterministic planner, verification logic, and risk model do not claim LLM or external-search results. The shared demo fixture is explicitly fictional; its pre-seeded scores and alerts are illustrative display data.

## Autonomous monitoring

Monitoring is enabled per owned investigation after its plan and verification state exist; demo investigations are rejected. `monitoring_configs` stores the interval, enabled/status fields, scheduled timestamps, max autonomous depth, last error, latest snapshot, and compact investigation memory. `monitoring_runs` stores each run and its result, `monitoring_snapshots` stores canonical JSON state plus a SHA-256 graph version, `investigation_changes` stores before/after values and evidence IDs, and `agent_decisions` stores the selected action, reason, status, and optional child investigation. Per-investigation unique keys suppress repeated changes and decisions.

The snapshot hash covers persisted investigation settings, entity identity/metadata, relation endpoints/status/metadata, evidence/source metadata and freshness, saved risk scores and factors, verification counts, active watch state, and alert state. Decision rules are deterministic. New upstream edges can trigger a child investigation; changed evidence can trigger the existing verification and risk services; risk deltas can trigger the existing risk calculation and alert rules. Conflicts and unsupported events request human review. A run starts no more than three follow-ups, uses a maximum depth of three, carries visited entity/relation IDs and query/source hashes across the chain, and suppresses repeated targets and queries. Child monitors inherit the parent interval and depth cap so an enabled scheduler can continue a chain within those bounds.

The scheduler is opt-in (`MONITORING_SCHEDULER_ENABLED=false` by default), uses an in-process polling task, and runs only one scheduler per application process. For manual-only operation the authenticated `POST /api/investigations/{id}/monitor/run` endpoint runs immediately. The monitoring REST routes, timeline events, and existing investigation WebSocket all enforce owner access. Autonomous actions stay within planning, research, verification, risk, and existing alert services; they do not send messages or make external operational changes. Decision rows contain a concise reason and trace links rather than internal reasoning traces.

## Risk graph inputs

Risk analysis reads one investigation's persisted entities, relationships, and linked evidence. Only a relationship with status `VERIFIED` and no demo marker enters the dependency graph. Evidence contributes to freshness only when its ID appears in that relationship's `verification.supporting_evidence_ids`. Conflict, rejection, insufficient evidence, and unsupported relationship states remain visible in relationship status counts and reports; they are not treated as verified edges.

The supported edge orientation is consumer → provider. Relationship types such as `DEPENDS_ON`, `USES`, and `PURCHASES_FROM` retain their stored direction. Provider-to-consumer relations such as `SUPPLIES`, `PROVIDES`, and `MANUFACTURES_FOR` are reversed for the dependency graph. Unknown types do not get an inferred direction.

## Scores and factors

Scores use a 0–100 scale. Each final score is a weighted mean over factors whose inputs are known; weights for unknown factors are omitted from the denominator. A missing value remains `UNKNOWN`. Factor explanations include their data source and relevant evidence IDs.

Default factor weights:

| Factor | Entity | Relationship | Meaning |
| --- | ---: | ---: | --- |
| Dependency depth | 0.20 | 0.15 | Reachable hops from one uniquely resolved investigation target |
| Verified dependency count | 0.20 | 0.15 | Structural proxy for the count of recorded direct options; not market share |
| Dependency centrality | 0.15 | 0.10 | Verified incident edges normalized to the most connected entity |
| Geographic concentration | 0.15 | 0.10 | Share of direct dependencies with a known, repeated jurisdiction |
| Recorded criticality | 0.10 | 0.15 | Criticality only when recorded metadata has source/evidence provenance |
| Verification uncertainty | 0.10 | 0.15 | `100 × (1 − verified relationship confidence)`; absent confidence stays unknown |
| Evidence age | 0.10 | 0.10 | Age of the oldest linked supporting evidence, capped at 100 at 365 days |
| Propagated exposure | — | 0.10 | Calculated provider exposure used by relationship assessments |

Level boundaries are configurable in `RiskConfig`: MEDIUM ≥25, HIGH ≥50, CRITICAL ≥75. Below 25 is LOW. Entity propagation begins with local weighted scores and passes provider exposure toward consumers across verified edges. Each hop applies relationship confidence and a default decay of 0.72; traversal stops after six hops and is cycle bounded. Final entity exposure is the greater of local score and propagated score, so the same exposure is not repeatedly added around a graph cycle.

Supplier count and market share are separate concepts. The entity factor uses `100 / verified direct dependency count` and is named as a count proxy. A measured share-based concentration index is available only when every share has its own `share_source`, `volume_share_source`, `share_evidence_ids`, or `volume_share_evidence_ids` provenance. Geography uses only stored jurisdiction values and reports its known-jurisdiction denominator.

Critical dependency patterns include single source, source-backed high concentration, recorded geographic concentration, deep dependency, material dependency, and a provider shared by multiple verified consumers. Pattern messages state when the graph does not establish market share, exclusivity, substitute availability, or real-world criticality.

## Snapshot and alert behavior

Each successful analysis writes an opaque `snapshot_id` on all risk rows and on `investigation.risk_analysis`. API list views use only the active snapshot; historical risk rows remain stored. Existing scores are explicitly labeled `fraction` during migration so legacy values such as `0.72` display as `72/100`. New scores use `percent`.

Alerts are deterministic events derived from persisted state: high-risk threshold crossing, a score increase of at least 10 points, new dependency patterns or verified edges, stale supporting evidence, verification conflict, and a watchlist threshold crossing. The deduplication key combines investigation, target, event type, owner, and relevant state. A later state change can produce a new alert. A still-breached watch threshold does not create a repeated alert until it first returns below threshold.

Non-demo alerts belong to their investigation owner. Read and dismiss actions on shared demo alerts use `alert_receipts` keyed by `(alert_id, user_id)`, so one user's action does not change another user's inbox. Dashboard unread counts use the same per-user view.

## Watchlists and reports

Watchlist targets are `entity`, `relationship`, `investigation`, or `risk_condition`. Entries have a user owner, target key, optional 0–100 threshold, and JSON condition. Risk evaluation stores `last_observed` so threshold changes are edge triggered. A watchlist row does not create a risk score; it only observes a saved calculated snapshot.

Report JSON includes the persisted plan, research state, sources, evidence, entity-resolution results, relationship states, graph counts, risk snapshot, alerts, unknown factors, conflicts, and lifecycle timeline. Plain text is a readable summary. CSV is a record-oriented export for spreadsheet review; cells beginning with formula markers are escaped. Demo status is carried into reports and exports.

## Access boundaries

Protected routes require authentication. Non-admin reads and writes resolve the parent investigation before returning or changing entities, relationships, evidence, risk snapshots, alerts, and reports. Risk queries filter to the active investigation snapshot. User watchlist entries are private. The only cross-user non-admin data is the shared, ownerless, fictional demo fixture. No collaboration or organization-sharing model is implemented.

## Database change

Revision `0007_risk_alerts_reports` follows `0006_verification_ownership`. It adds risk progress/snapshot fields, alert metadata and receipts, user-owned multi-target watchlists, and structured reports. Revision `0008_autonomous_monitoring` follows 0007, adds the investigation's autonomous context JSON and creates monitoring configuration, run, snapshot, change, and decision tables. Both revisions are additive; no investigation, evidence, relationship, risk, report, watchlist, or alert record is deleted. The old entity-only watchlist uniqueness constraint is replaced by an owner-and-target constraint, and entity IDs become nullable so other target types can be stored.

The migrations are forward-only by design; their downgrade paths raise errors instead of deleting feature columns or data. Run `python -m alembic upgrade head` and `python -m alembic check` against the configured database after recording the pre-upgrade schema and row counts.

## Phase 8 production hardening

The investigation is row-locked while research, verification, risk analysis, or monitoring is started. These transactions re-read current state before validating a transition, so simultaneous requests cannot both start the same persisted lifecycle step. Report generation builds and renders its content before committing the completion transition and report row; on failure the transaction rolls back and the API records a safe `report_generation_failed` lifecycle event without changing the last valid investigation status.

JSON model columns use a PostgreSQL JSONB variant and remain portable to SQLite test databases. Alembic compares the model against the existing PostgreSQL JSONB columns without proposing a type change. The workspace graph selects a bounded page of entity and relationship rows before loading related risk and evidence details: default 500 entities and 1,000 relationships, with a request limit from 25 to 1,000 entities and an entity `offset`. The response reports entity-page and relationship truncation separately; the UI provides previous/next entity-page controls. Each relationship includes at most its three most recent linked evidence previews and its full evidence count. Entity list canonical-name and fallback evidence-source enrichment uses batched lookups instead of one query per entity.

The final audit ran the backend suite, Python compilation, TypeScript and Vite production build, Playwright browser flow, `alembic upgrade head`, and `alembic check`. A post-upgrade row count and referential-integrity snapshot is recorded in `TEST_REPORT.md`. Security tests cover missing, malformed, expired, and revoked tokens; owner boundaries on investigation, risk, report, watchlist, monitoring, agent-decision, and WebSocket routes; and cross-investigation query isolation. WebSocket ownership is rechecked before every send, including after an ownership change during a connection. Authentication throttling is not configured. CORS is restricted to the configured origins; browser API requests use bearer tokens, while WebSocket connections validate origin, bearer token, and investigation owner.

## Known limits

- No external research provider is configured; a real risk snapshot requires verified relationships from actual persisted sources.
- Risk factors are deterministic heuristics and need calibration against reviewed supply-chain data before operational use.
- Market-share, capacity, substitute, financial-health, and jurisdiction values remain unknown unless a source-backed value is persisted.
- In-process background work is not durable across restarts.
- The monitoring scheduler runs in one application process and needs durable coordination before enabling it on multiple API workers.
- No external research provider is configured, so autonomous follow-ups currently exercise the persisted pipeline but do not discover real external sources.
- There is no team sharing, tenant workspace, or organization role model.
- Login and registration endpoints do not have distributed rate limiting; deployments exposed to the public internet need a shared rate limiter.
- E2E and backend test runs use isolated SQLite databases. PostgreSQL migration and integrity results are reported separately in `TEST_REPORT.md`.
