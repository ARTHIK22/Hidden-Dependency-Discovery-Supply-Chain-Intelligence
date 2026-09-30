# Frontend ↔ backend integration map

This map reflects the checked-in implementation, not the feature names in the UI. Backend routes are mounted under `/api/v1`. The frontend has no WebSocket counterpart in the backend; the existing investigation detail page's `ws://.../ws/...` connection was not a valid backend contract.

## Shared transport and authentication

| Frontend feature / UI | Frontend API function | HTTP method and endpoint | Auth | Request → backend schema | Backend service/model → response | Frontend type / status |
|---|---|---|---|---|---|---|
| Login page → auth API/store | `login` | `POST /auth/login` | Public | `LoginRequest { email, password }` | auth service → `User`; `TokenResponse { access_token, token_type, user }` | `TokenResponse`, `User`; 200, 401, 422 |
| Register page → auth API/store | `register` | `POST /auth/register` | Public | `RegisterRequest { email, password, full_name }` | auth service → `User`; `TokenResponse` | `TokenResponse`, `User`; 201, 409, 422 |
| Protected route/session restore | `getCurrentUser` | `GET /auth/me` | Bearer JWT | none | auth dependency → `UserRead` | `User`; 401 |
| Profile settings | `updateProfile` | `PATCH /users/me` | Bearer JWT | `{ full_name }` | user service → `UserRead` | `User`; 200, 401, 422 |
| All API calls | shared `apiClient` | `/api/v1` base URL | adds `Authorization: Bearer ...` | JSON/query/body | FastAPI JSON/errors; 401 clears local session | typed response/error mapping |

## Main data modules

| Frontend feature / UI | Frontend API function | HTTP method and endpoint | Request → schema | Backend service/model → response | Status / limitations |
|---|---|---|---|---|---|
| Dashboard and investigation list | `listInvestigations` | `GET /investigations?status&limit&offset` | query | `Investigation` → array `InvestigationRead` | 200; user-owned only |
| Create investigation | `createInvestigation` | `POST /investigations` | `InvestigationCreate { name, target?, description?, priority? }` | `Investigation` → `InvestigationRead` | 201, 401, 422 |
| Investigation overview/details | `getInvestigation` | `GET /investigations/{id}` | UUID path | ownership service → `InvestigationRead` | 200, 404 |
| Investigation edit | `updateInvestigation` | `PATCH /investigations/{id}` | `InvestigationUpdate` | `Investigation` → `InvestigationRead` | 200, 404, 409, 422 |
| Start/resume / pause / archive controls | `startInvestigation`, `pauseInvestigation`, `archiveInvestigation` | `POST /investigations/{id}/start`, `POST /investigations/{id}/pause`, `DELETE /investigations/{id}` | UUID path | synchronous local workflow / investigation → `InvestigationRead` or 204 | start runs stored-data workflow; external research is skipped; pause cannot interrupt synchronous work; delete archives |
| Investigation timeline | `getInvestigationSteps` | `GET /investigations/{id}/steps` | UUID path | `InvestigationStep` → ordered array | 200, 404; `research` may be `skipped` |
| Entity list/search | `listEntities` | `GET /entities?q&limit&offset` | query | entity service/model → array `EntityRead` | 200; authenticated catalog |
| Entity create/detail/update | `createEntity`, `getEntity`, `updateEntity` | `POST /entities`, `GET /entities/{id}`, `PATCH /entities/{id}` | `EntityCreate`, UUID, `EntityUpdate` | entity service/model → `EntityRead` | 201/200, 404, 422 |
| Entity aliases | `addAlias`, `listAliases` | `POST /entities/{id}/aliases`, `GET /entities/{id}/aliases` | `AliasCreate { alias, alias_type }` | alias manager/model → alias object/list | 201/200, 404, 409 |
| Relationship list/details/create | `listRelationships`, `getRelationship`, `createRelationship` | `GET /relationships?entity_id&limit&offset`, `GET /relationships/{id}`, `POST /relationships` | query / UUID / `RelationshipCreate` | relationship service/model → `RelationshipRead` | 200/201, 404, 409 duplicate, 422 |
| Evidence-based verification | `verifyRelationship` | `POST /relationships/{id}/verify` | UUID | verifier + evidence/source records → `{ relationship, verification }` | 200, 404, 409 if no evidence |
| Evidence explorer | `listEvidence`, `createEvidence` | `GET /evidence?relationship_id&entity_id&limit&offset`, `POST /evidence` | query / `EvidenceCreate` | evidence service/model, content SHA256 → array or `EvidenceRead` | 200/201; write requires investigation ownership |
| Source list/create | `listSources`, `createSource` | `GET /sources?limit&offset`, `POST /sources` | query / `SourceCreate` | source model → array or `SourceRead` | 200/201 |
| Dependency graph | `getGraph` | `GET /graph/{entity_id}?depth` | UUID + depth 1..5 | graph service → `{ nodes, edges }` | 200, 404; graph is neighborhood around one entity |
| Dependency path | `getDependencyPath` | `GET /graph/path/{source_id}/{target_id}` | UUID pair | path finder → `{ path, hops }` | 200, 404; undirected shortest path |
| Risk center/summary | `getRiskAnalysis` | `GET /risks/analysis` | none | risk service/graph heuristics → `{ risks, basis, external_risk_feeds_used }` | 200; stored relationship heuristics only |
| Alerts list/read | `listAlerts`, `markAlertRead` | `GET /alerts?unread&limit`, `POST /alerts/{id}/read` | query / UUID | alert model → list or alert | 200, 404; no full create/resolve lifecycle |
| Watchlist | `listWatchlist`, `addToWatchlist`, `removeFromWatchlist` | `GET /watchlists`, `POST /watchlists/{entity_id}?name`, `DELETE /watchlists/{entity_id}` | query / UUID | watchlist service/model → list/item/204 | 200/201/204, 404; user-scoped |
| Reports | `generateReport` | `POST /reports/investigations/{id}` | UUID | report service/model → `{ id, investigation, entities, relationships, evidence, sources, risks, ... }` | 200, 404; stored data only |
| Graph export | `exportGraph` | `GET /exports/graph.json` | none | export service/models → JSON `{ nodes, edges }` | 200; file not required |
| Relationship export | `exportRelationshipsCsv` | `GET /exports/relationships.csv` | none | export service/model → `text/csv` attachment | 200 |
| Health/readiness | `getHealth`, `getReadiness` | `GET /health`, `GET /health/ready` | Public | DB/Redis checks → status JSON | 200; Redis optional/unavailable may be reported |

## Current UI wiring and gaps

The source tree contains the feature/page names above, but most `features/*/*.api.ts`, the shared HTTP client, auth store/routes and many reusable widgets were empty at audit time. `CreateInvestigation.tsx` called the nonexistent `/api/investigations/` with an incompatible body. Dashboard and investigation detail contained fixed sample numbers. The investigation detail attempted a WebSocket endpoint not present in FastAPI. The app route table did not expose the login/register routes or protect private pages. These were the integration targets.

The backend does not expose entity or relationship DELETE routes, report listing, alert get/resolve, dashboard statistics, or WebSocket updates; the frontend must not imply those operations are available. Investigation DELETE is archive (204), not permanent removal.

### Active page → request wiring

| Active route/page | Requests currently made by the page |
|---|---|
| `/login`, `/register` | Auth API; saves the access token and user then navigates to protected routes |
| `/` dashboard | Investigations, entities, relationships, sources and risk analysis (bounded lists; not aggregate totals) |
| `/investigations` | Paginated list and archive; start/resume draft, paused or failed work |
| `/investigations/new` | Create, then synchronously start the stored-data workflow |
| `/investigations/:id` | Get investigation, get steps, start/resume and refresh timeline |
| `/entities` | Search/list and create; detail/edit/alias calls are available in API module but not exposed in this list screen |
| `/relationships` | List and client-side search; create/get/verify API methods exist but no create/verification form is connected |
| `/evidence` | List evidence and supporting sources/entities/relationships; evidence create method exists but no create form is connected |
| `/sources` | List and register source metadata |
| `/graph` | Export recorded graph, risk signals, shortest path API; searches/filters are over fetched records |
| `/risks` | Backend risk analysis and client-side text search |
| `/alerts` | List/unread filter/mark read |
| `/watchlist` | List/add/remove and entity lookup |
| `/reports` | List investigations, generate report and download response as JSON; no saved report history endpoint exists |

Some legacy routes/components and feature hook files remain empty or unused. They are not counted as integrated. The active pages above use real backend data for the operations listed, and UI gaps are called out rather than represented as working CRUD.
