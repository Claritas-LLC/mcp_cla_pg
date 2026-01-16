## Goals
- Spin up a temporary PostgreSQL 9.6 container with deterministic sample data.
- Programmatically call every `@mcp.tool` exposed by this repo and assert results are sane and accurate.
- Fail fast on any tool runtime error, then fix the implementation until the full suite passes.
- Tear down (drop) the container and volumes after tests complete.

## Current Findings (Why tests will fail today)
- `server.py` has duplicate tool definitions near the end (e.g., `ping`, `server_info`, `run_query`, etc.), which can cause confusion and non-deterministic tool registration.
- Several queries are not PostgreSQL 9.6 compatible (e.g., `db_stats` selects `checksum_failures`, which doesn’t exist on 9.6).
- `analyze_table_health` references fields that aren’t selected (e.g., `seconds_since_vacuum` / `seconds_since_analyze`), which will throw at runtime.
- README lists tools that are not currently implemented in `server.py` (not a test blocker, but we’ll base “all tools” on actual `@mcp.tool` registrations).

## Approach
### 1) Create an integration test harness (real container, real DB)
- Add a dedicated docker compose file (or extend existing compose) that starts:
  - `postgres:9.6` with a known user/password/db.
- Add an initialization step that loads sample schema + data:
  - Tables: `customers`, `orders`, `order_items`
  - Indexes on common access patterns (e.g., `orders(customer_id, created_at)`)
  - Some churn (insert + delete) to make bloat/maintenance tools return meaningful output.

### 2) Call tools via FastMCP Client (in-memory server instance)
- Use FastMCP’s Python `Client` with an in-memory transport (connect directly to the `mcp` object) so we can:
  - Call `list_tools()` to enumerate the authoritative tool list.
  - `call_tool(name, args)` for each tool using deterministic inputs.
- Still uses the real Postgres container because `server.py` connects via `DATABASE_URL`.
- This tests the actual tool execution paths without needing to run the HTTP server in a second process.

### 3) Define “desired outcome” assertions per tool
For each tool we’ll assert:
- It returns the expected shape (dict/list keys), and values are plausible.
- It behaves correctly on Postgres 9.6.

Examples:
- `ping` → `{ok: true}`
- `server_info` → includes `version`, `allow_write`, etc.
- `run_query` (read-only) → returns columns/rows; rejects writes when `MCP_ALLOW_WRITE=false`.
- `db_stats` → includes our test database; no invalid columns for 9.6.
- `check_bloat` → returns list; each row contains `maintenance_cmd`.
- `create_db_user`/`drop_db_user`/`kill_session` → succeed when `MCP_ALLOW_WRITE=true`.

### 4) Fix tool implementation issues uncovered by tests
Planned fixes (based on current code review):
- Remove duplicate tool definitions at the bottom of `server.py`.
- Make `db_stats` compatible with Postgres 9.6 by selecting only columns that exist (or branch by `server_version_num`).
- Fix `analyze_table_health` to compute “seconds since vacuum/analyze” correctly (or avoid those fields and rely on timestamps).
- Any additional 9.6 catalog differences encountered will be fixed with version gating.

### 5) Run suite and teardown
- Start container.
- Run tests.
- On success: stop and remove containers + volumes.
- On failure: keep container long enough to debug, fix code, rerun, then teardown.

## Files/Artifacts to Add or Update
- Update: `server.py` (dedupe tools + Postgres 9.6 compatibility fixes).
- Add: a docker-compose file for test Postgres 9.6 (or extend existing compose with a `postgres96` service).
- Add: a small SQL init script for sample data.
- Add: a Python integration test runner (pytest) that:
  - boots container
  - loads sample data
  - calls all tools via FastMCP Client
  - asserts outcomes
  - tears down

## Execution (what I’ll do after you confirm)
- Implement the fixes + test harness.
- Run: docker compose up (pg96) → run pytest → docker compose down -v.
- Report a per-tool pass/fail summary and any behavior notes.

If you confirm, I’ll start implementing immediately and run the full integration suite end-to-end.