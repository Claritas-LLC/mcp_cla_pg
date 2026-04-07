---
goal: Add instance-aware DB session table beneath the session monitor line graph
version: 1.0
date_created: 2026-04-07
last_updated: 2026-04-07
owner: Platform DBA Tooling
status: Planned
tags: [feature, monitoring, ui, api, sessions, dual-instance]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan defines deterministic work to extend the session monitor so the page at `/sessions-monitor` renders a per-session table directly below the existing line graph, sourced from the same selected database instance as the chart and summary counters.

## 1. Requirements & Constraints

- REQ-001: Add a session table directly below the existing `<canvas id="sessionsChart">` region inside `SESSION_MONITOR_HTML` in `server.py`.
- REQ-002: The table must render only sessions from the instance selected by the `instance` query parameter on `/sessions-monitor`.
- REQ-003: The table must use a dedicated HTTP endpoint at `GET /api/sessions/list?instance=01|02` implemented in `server.py`.
- REQ-004: The table must display exactly these columns in this order: `PID`, `database name`, `username`, `application name`, `client address`, `client hostname`, `session start`, `wait event`, `state`, `query`.
- REQ-005: The SQL used by `GET /api/sessions/list` must project these aliases exactly: `pid`, `database_name`, `username`, `application_name`, `client_address`, `client_hostname`, `session_start`, `wait_event`, `state`, `query`.
- REQ-006: The backend column label `session start` must be sourced from PostgreSQL `backend_start` and renamed in SQL as `session_start`.
- REQ-007: The frontend must refresh the table on the same polling cycle as the summary chart so both views remain aligned to the same instance and timestamp window.
- REQ-008: The response payload for `GET /api/sessions/list` must include instance metadata and collection metadata: `instance_id`, `host`, `database`, `count`, `sessions`, `timestamp`.
- REQ-009: The table rendering logic must tolerate null database fields by displaying a deterministic fallback string such as `-` for missing text values.
- REQ-010: The existing `GET /api/sessions` summary endpoint and chart behavior must remain backward compatible.
- SEC-001: Reject unsupported `instance` values with HTTP `400` and deterministic JSON payload `{ "ok": false, "error": "Unsupported database instance id", "instance": "<input>" }`.
- SEC-002: Do not expose connection credentials, SQL parameters, or internal exception traces in the new list API.
- SEC-003: Return session query text as read-only display data only; do not add UI actions that terminate or modify sessions.
- CON-001: Reuse `_normalize_instance_id`, `_run_in_instance_sync`, `_resolve_instance_metadata`, `pool.connection()`, and `_execute_safe` in `server.py`.
- CON-002: Keep this feature implemented within existing inline HTML/JavaScript in `SESSION_MONITOR_HTML`; do not introduce a templating engine or separate frontend build pipeline.
- CON-003: Preserve the existing instance selector URL model (`/sessions-monitor?instance=01|02`) without adding local storage or cookie state.
- CON-004: Align implementation with the already-present unstaged expectations in `README.md` and `tests/test_tools_pg96.py` rather than changing those expectations.
- GUD-001: Use deterministic DOM ids for new elements, including `sessionsTableBody`, to support static tests and future UI automation.
- GUD-002: Render long query text in a readable but bounded table cell using CSS wrapping or max-width constraints instead of truncating the column header set.
- PAT-001: Use one fetch path for summary metrics (`/api/sessions`) and one fetch path for row details (`/api/sessions/list`), both parameterized by the same resolved instance.
- PAT-002: Order session rows by `backend_start DESC NULLS LAST, pid DESC` for stable, newest-session-first rendering.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Add an instance-aware session list API that returns all DB sessions for the selected instance with the exact projection required by the UI.

| Task | Description | Completed | Date |
| -------- | --------------------- | --------- | ---------- |
| TASK-001 | In `server.py`, add `@mcp.custom_route("/api/sessions/list", methods=["GET"])` adjacent to existing `api_sessions` so all session-monitor HTTP routes remain co-located. |  |  |
| TASK-002 | Implement `api_sessions_list(request: Request) -> JSONResponse` in `server.py` to parse `instance` from query params, normalize it with `_normalize_instance_id`, and return the same `400` validation payload used by `api_sessions` for invalid instance ids. |  |  |
| TASK-003 | Inside `api_sessions_list`, execute the SQL via `_run_in_instance_sync(normalized_instance, _query_fn)` so the list endpoint resolves the correct pool for instance `01` or `02` deterministically. |  |  |
| TASK-004 | In the new `_query_fn`, query `pg_stat_activity` selecting `pid`, `datname AS database_name`, `usename AS username`, `application_name AS application_name`, `client_addr::text AS client_address`, `client_hostname AS client_hostname`, `backend_start AS session_start`, `wait_event AS wait_event`, `state AS state`, and `query AS query`. |  |  |
| TASK-005 | In the same SQL, exclude no requested columns, keep all sessions visible for the selected instance scope, and append `ORDER BY backend_start DESC NULLS LAST, pid DESC` exactly to guarantee stable ordering and satisfy the existing static test contract. |  |  |
| TASK-006 | Build the JSON response in `api_sessions_list` with `_resolve_instance_metadata(normalized_instance)` and return `{ "instance_id": <id>, "host": <host>, "database": <name>, "count": <len(sessions)>, "sessions": <rows>, "timestamp": time.time() }`. |  |  |

### Implementation Phase 2

- GOAL-002: Extend the monitor page to render the session table directly beneath the chart and keep it synchronized with the selected instance.

| Task | Description | Completed | Date |
| -------- | --------------------- | --------- | ---------- |
| TASK-007 | In `SESSION_MONITOR_HTML` within `server.py`, add a new section immediately after `<canvas id="sessionsChart"></canvas>` containing a table wrapper, a `<thead>` with the exact required headers, and `<tbody id="sessionsTableBody"></tbody>`. |  |  |
| TASK-008 | Add CSS in the existing `<style>` block for table layout, overflow handling, sticky readability, and wrapped query text so the table remains usable on desktop and smaller screens without changing the page routing model. |  |  |
| TASK-009 | In the existing inline JavaScript, add a pure function `renderSessionsTable(rows)` that empties `sessionsTableBody` and appends one `<tr>` per session using the exact response fields `pid`, `database_name`, `username`, `application_name`, `client_address`, `client_hostname`, `session_start`, `wait_event`, `state`, and `query`. |  |  |
| TASK-010 | In `renderSessionsTable`, normalize null or empty text values to `-`, preserve raw query text as display content, and avoid inserting HTML from the API payload by assigning text content per cell rather than concatenating unsanitized markup. |  |  |
| TASK-011 | Refactor the existing `fetchData()` logic into either a combined async routine or two coordinated requests so each refresh cycle fetches both `/api/sessions?instance=<resolved>` and `/api/sessions/list?instance=<resolved>`, updates the chart/stat tiles, then calls `renderSessionsTable(sessionsPayload.sessions);`. |  |  |
| TASK-012 | Keep table refresh tied to the existing `setInterval(fetchData, 5000);` cadence so the chart and table always represent the same selected instance and near-identical sample time. |  |  |
| TASK-013 | Add a table empty-state row when `sessionsPayload.sessions` is empty, with a single full-width message such as `No sessions returned for this instance.` so the page remains explicit instead of blank. |  |  |

### Implementation Phase 3

- GOAL-003: Align automated coverage and documentation with the session table feature and existing unstaged repository changes.

| Task | Description | Completed | Date |
| -------- | --------------------- | --------- | ---------- |
| TASK-014 | Preserve and satisfy the existing static assertions already added in `tests/test_tools_pg96.py` for the new route, SQL aliases, header labels, `sessionsTableBody`, and `renderSessionsTable(sessionsPayload.sessions);` call site. |  |  |
| TASK-015 | Extend `tests/test_tools_pg96.py` or add a focused HTTP route test module to verify `GET /api/sessions/list?instance=01` returns `200` with keys `instance_id`, `host`, `database`, `count`, `sessions`, and `timestamp`. |  |  |
| TASK-016 | Add a negative test for `GET /api/sessions/list?instance=03` asserting HTTP `400` and the same deterministic validation payload shape used by `/api/sessions`. |  |  |
| TASK-017 | Add UI-oriented assertions that `SESSION_MONITOR_HTML` contains the exact header labels required by the user, places the table below the chart markup, and includes the `renderSessionsTable` invocation in the polling flow. |  |  |
| TASK-018 | Update `README.md` session-monitor documentation to describe the new list endpoint and the table columns exactly as already reflected in the current unstaged README diff. |  |  |

## 3. Alternatives

- ALT-001: Reuse `/api/sessions` by embedding full row details into the summary payload. Rejected because it couples fast-changing summary metrics with heavier per-session payloads and risks breaking existing consumers of the compact response.
- ALT-002: Build the table entirely from the existing `db_pg96_analyze_sessions` tool output. Rejected because that tool is threshold-based and segmented into active/idle/locked groups, not a complete all-sessions list for the selected instance.
- ALT-003: Render the session list server-side into HTML at page load only. Rejected because the monitor already uses client polling and the table must stay synchronized with live summary updates.
- ALT-004: Add pagination or filtering in the first increment. Rejected because the user requested a complete list of all DB sessions with specific columns, and no paging/filtering requirement was provided.

## 4. Dependencies

- DEP-001: `server.py` `SESSION_MONITOR_HTML` inline page definition and existing `sessions_monitor(request: Request)` route.
- DEP-002: `server.py` `api_sessions(request: Request)` summary route for existing chart/stat behavior.
- DEP-003: `server.py` helpers `_normalize_instance_id`, `_run_in_instance_sync`, `_resolve_instance_metadata`, and `_execute_safe`.
- DEP-004: PostgreSQL `pg_stat_activity` catalog view, including fields `pid`, `datname`, `usename`, `application_name`, `client_addr`, `client_hostname`, `backend_start`, `wait_event`, `state`, and `query`.
- DEP-005: Existing unstaged repository changes in `README.md` and `tests/test_tools_pg96.py` that already define the intended endpoint and UI contract.

## 5. Files

- FILE-001: `server.py` - add `api_sessions_list`, extend `SESSION_MONITOR_HTML`, add client-side table rendering, and wire polling to fetch list data for the selected instance.
- FILE-002: `tests/test_tools_pg96.py` - preserve static assertions and expand targeted checks for route shape and UI markers if the project keeps static-source validation in this module.
- FILE-003: `README.md` - document `/api/sessions/list`, the response shape, and the new session table behavior in the monitor page.
- FILE-004: `plan/feature-session-monitor-sessions-table-1.md` - authoritative execution plan for this feature.

## 6. Testing

- TEST-001: `GET /api/sessions/list` defaults to instance `01` when `instance` is omitted.
- TEST-002: `GET /api/sessions/list?instance=01` returns `200` with payload keys `instance_id`, `host`, `database`, `count`, `sessions`, and `timestamp`.
- TEST-003: `GET /api/sessions/list?instance=02` returns `200` with the same payload shape and rows sourced from instance `02` through `_run_in_instance_sync`.
- TEST-004: `GET /api/sessions/list?instance=03` returns `400` with payload `{ "ok": false, "error": "Unsupported database instance id", "instance": "03" }`.
- TEST-005: Source-level UI test confirms the monitor HTML contains headers `PID`, `database name`, `username`, `application name`, `client address`, `client hostname`, `session start`, `wait event`, `state`, and `query`.
- TEST-006: Source-level UI test confirms `id="sessionsTableBody"` exists and the polling flow invokes `renderSessionsTable(sessionsPayload.sessions);`.
- TEST-007: Manual browser validation of `/sessions-monitor?instance=01` shows the table below the chart and rows update every 5 seconds.
- TEST-008: Manual browser validation of `/sessions-monitor?instance=02` shows the same table layout but backed by instance `02` metadata and rows.
- TEST-009: Manual empty-state validation confirms the table shows a deterministic no-results message instead of a blank body when zero sessions are returned.

## 7. Risks & Assumptions

- RISK-001: The monitor page is built as an inline HTML string, so adding substantial table markup and JavaScript increases the chance of quoting or syntax regressions in `server.py`.
- RISK-002: `pg_stat_activity.query` can contain very long SQL text, which may create layout issues unless CSS wrapping and scroll behavior are handled explicitly.
- RISK-003: Concurrent polling of summary and list endpoints can briefly show slightly different snapshots if the database changes between the two queries; this is acceptable unless strict transactional consistency is later required.
- RISK-004: Some PostgreSQL sessions may have null `client_hostname` or `client_addr`, so the UI must normalize missing values to avoid inconsistent rendering.
- ASSUMPTION-001: The intended scope of “all DB sessions in the corresponding instance” is all rows visible from `pg_stat_activity` on that selected PostgreSQL instance, not an application-filtered subset.
- ASSUMPTION-002: The current unstaged `README.md` and `tests/test_tools_pg96.py` changes are intentional and should be treated as acceptance criteria, not reverted.
- ASSUMPTION-003: Existing monitor consumers rely on `/api/sessions` remaining compact, so the new row-level data belongs in a separate route.

## 8. Related Specifications / Further Reading

- [server.py](../server.py)
- [README.md](../README.md)
- [tests/test_tools_pg96.py](../tests/test_tools_pg96.py)
- [feature-session-monitor-instance-routing-1.md](feature-session-monitor-instance-routing-1.md)