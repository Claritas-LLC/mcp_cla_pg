# PostgreSQL MCP Server (Python + Docker)

Remote MCP server that exposes PostgreSQL DBA-oriented tools over Streamable HTTP, designed to be consumed by MCP-capable clients (including Codex – OpenAI’s coding agent in VS Code).

## Overview

This server runs as an HTTP service and provides:

- Read-only safe database inspection by default (writes disabled unless explicitly enabled)
- Common DBA discovery and monitoring tools (schemas, tables, sizes, sessions, query stats)
- Ad-hoc SQL execution with a configurable row limit
- EXPLAIN plan generation for query performance analysis

The MCP endpoint is served at:

- `http://<host>:<port>/mcp`

Health endpoint:

- `http://<host>:<port>/health`

## Tools Exposed

The MCP server exposes these tools:

- `ping`: Health check.
- `server_info`: Get database version, user, and server settings.
- `db_stats`: Get database-level statistics (commits, rollbacks, temp files, deadlocks) with optional performance metrics.
- `analyze_sessions`: Comprehensive session analysis combining active queries, idle sessions, and locks.
- `analyze_table_health`: Comprehensive table health analysis combining bloat detection, maintenance needs, and autovacuum recommendations.
- `analyze_indexes`: Identify unused, duplicate, missing, and redundant indexes.
- `recommend_partitioning`: Suggest tables for partitioning based on size and access patterns.
- `recommend_materialized_views`: Analyze access patterns and recommend tables for materialized view conversion.
- `recommend_autovacuum_settings`: Analyze tables and recommend autovacuum settings based on data access patterns.
- `database_security_performance_metrics`: Analyze security and performance metrics with optimization recommendations.
- `get_db_parameters`: Retrieve database configuration parameters (GUCs) with optional filtering.
- `list_databases`: List all available databases and their sizes.
- `list_schemas`: List schemas in the current database.
- `list_largest_schemas`: List schemas ranked by total size (tables, indexes, toast).
- `list_temp_objects`: List temporary schemas with object counts and total size.
- `list_tables`: List tables in a specific schema.
- `list_largest_tables`: List the largest tables in a specific schema ranked by size.
- `describe_table`: Get column details, indexes, and sizes for a table.
- `run_query`: Execute ad-hoc read-only SQL queries (with row limits).
- `explain_query`: Generate EXPLAIN plans for query analysis.
- `create_db_user`: Create a new database user and assign read or read/write privileges (requires `MCP_ALLOW_WRITE=true`).
- `drop_db_user`: Drop an existing database user (requires `MCP_ALLOW_WRITE=true`).
- `kill_session`: Terminate a database session by its PID (requires `MCP_ALLOW_WRITE=true`).

### Applying recommendations

Several tools (for example `analyze_table_health`, `recommend_autovacuum_settings`, and `database_security_performance_metrics`) generate maintenance and tuning recommendations such as `VACUUM`, `ALTER TABLE ... SET (autovacuum_*)`, or changes to `postgresql.conf` parameters. These tools are **read-only**:

- They never execute `VACUUM`, `VACUUM FULL`, `ANALYZE`, `ALTER TABLE`, or `ALTER SYSTEM`.
- They do not modify `postgresql.conf` or any database settings.
- They only return suggested commands and configuration values that you can apply elsewhere.

To actually implement the recommendations you must:

- Review the suggested SQL or configuration changes.
- Apply them using your normal administration channel (psql, pgAdmin, migration scripts, or a separate write-enabled workflow).

Even when `MCP_ALLOW_WRITE=true`, this server only exposes a very small set of write-capable tools (`create_db_user`, `drop_db_user`, `kill_session`) and does **not** provide a generic “apply recommendations” or “run arbitrary maintenance SQL” tool.

## How to Use

### Typical flow

1. Start the container (read-only recommended).
2. Add the MCP server URL to your VS Code MCP client.
3. In chat, verify connectivity with `ping` and `server_info`.
4. Explore schema with `list_schemas` → `list_tables` → `describe_table`.
5. Use `run_query` for ad-hoc SELECTs (row-limited).
6. Use `explain_query` to inspect query plans before changing indexes/SQL.

### Example prompts (VS Code / Codex)

Basic connectivity:

- “Using `postgres_readonly`, call `ping` and show the result.”
- “Using `postgres_readonly`, call `server_info` and summarize database/user/version.”
- “Using `postgres_readonly`, call `db_stats` for the current database and summarize activity (commits, temp files, deadlocks).”
- “Using `postgres_readonly`, call `get_db_parameters(pattern='max_connections|shared_buffers')` to check current capacity settings.”

Schema discovery:

- “Using `postgres_readonly`, call `list_schemas` (include_system=false).”
- “Using `postgres_readonly`, call `list_tables` for schema `public`.”
- “Using `postgres_readonly`, call `describe_table` for `public.orders` and summarize indexes and size.”

Ad-hoc query (read-only):

- “Using `postgres_readonly`, run this query with `run_query` and return the first 50 rows:
  `select * from public.orders order by created_at desc`”

Parameterized query (with `params_json`):

- “Using `postgres_readonly`, call `run_query` with:
  - sql: `select * from public.orders where id = %(id)s`
  - params_json: `{ \"id\": 123 }`”

Explain plan:

- “Using `postgres_readonly`, call `explain_query` (format=json, analyze=false) for:
  `select * from public.orders where customer_id = 42 order by created_at desc limit 50`
  Then interpret the plan and suggest indexes.”

Active session triage:

- “Using `postgres_readonly`, call `list_active_queries` and summarize the currently executing SQL statements.”
- “Using `postgres_readonly`, call `list_idle_sessions(min_idle_seconds=300)` to find long-running idle connections.”
- “Using `postgres_readonly`, call `active_sessions(min_duration_seconds=300)` and summarize what looks stuck.”

Lock triage:

- “Using `postgres_readonly`, call `db_locks(min_wait_seconds=30, limit=50)` and summarize blockers vs blocked.”

Capacity review:

- “Using `postgres_readonly`, call `list_largest_schemas(limit=30)` to identify the biggest schemas.”
- “Using `postgres_readonly`, call `list_temp_objects` to check for large or numerous temporary objects.”
- “Using `postgres_readonly`, call `list_largest_tables(schema='public', limit=30)` to find the largest tables in the public schema.”
- “Using `postgres_readonly`, call `table_sizes(limit=20)` and `index_usage(limit=20)`, then highlight the biggest objects.”
- “Using `postgres_readonly`, call `analyze_indexes(schema='public')` to find optimization opportunities.”
- “Using `postgres_readonly`, call `recommend_partitioning(min_size_gb=1.0)` to identify candidates for table partitioning.”
- “Using `postgres_readonly`, call `recommend_materialized_views(schema='public')` to find tables suitable for materialized view conversion.”
- “Using `postgres_readonly`, call `recommend_autovacuum_settings(min_size_mb=50)` to get autovacuum tuning recommendations.”
- “Using `postgres_readonly`, call `database_security_performance_metrics()` to analyze security and performance issues with optimization commands.”
- “Using `postgres_readonly`, call `analyze_table_health(schema='public')` to get comprehensive table health analysis including bloat, maintenance, and autovacuum recommendations.”
- “Using `postgres_readonly`, call `analyze_sessions()` to get comprehensive session analysis including active queries, idle sessions, and lock information.”
- “Using `postgres_readonly`, call `check_bloat(limit=50)` and summarize the top 10 most bloated objects and their fix commands.”
- “Using `postgres_readonly`, call `maintenance_stats` and identify tables with high dead tuple counts or freeze risk.”

User management (requires maintenance role):

- “Using `postgres_maintenance`, call `create_db_user(username='lenexa_analyst', password='change_me_123', privileges='read', database='lenexa')`”

- “Using `postgres_maintenance`, call `drop_db_user(username='old_analyst')`”

- “Using `postgres_maintenance`, call `kill_session(pid=1234)` to terminate a stuck session.”

## Requirements

### Runtime (recommended)

- Docker
- Network access from the container to PostgreSQL

### Development (optional)

- Python 3.12+
- Windows: if `pip install` fails with a TLS CA bundle error, use `python pipw.py install -r requirements.txt`.

## Configuration

### Database Connection

Provide one of the following:

- `DATABASE_URL` (recommended)
- or: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

Example:

- `DATABASE_URL=postgresql://mcp_readonly:password@db-host:5432/app_db`

### Safety / Limits

- `MCP_ALLOW_WRITE` (default: `false`)
  - `false`: only read-only queries are allowed (SELECT/WITH/SHOW/EXPLAIN)
  - `true`: write and DDL statements are allowed
- `MCP_MAX_ROWS` (default: `500`): default max rows returned by `run_query`
- `MCP_STATEMENT_TIMEOUT_MS` (default: `30000`): session-level query execution timeout in milliseconds.

### Connection Pool

- `MCP_POOL_MIN_SIZE` (default: `1`)
- `MCP_POOL_MAX_SIZE` (default: `5`)
- `MCP_POOL_TIMEOUT` (default: `30.0`): time in seconds to wait for a connection from the pool.
- `MCP_POOL_MAX_WAITING` (default: `10`): maximum number of requests waiting for a connection.

### Server Transport

- `MCP_TRANSPORT` (default: `http`): `http`, `sse`, or `stdio`
- `MCP_HOST` (default: `0.0.0.0`)
- `MCP_PORT` (default: `8000`)
- `MCP_SERVER_NAME` (default: `PostgreSQL MCP Server`)

### OAuth (OIDC) Authentication

To secure the remote endpoint with generic OAuth (OIDC) authentication, set the following environment variables:

- `FASTMCP_AUTH_TYPE=oidc`
- `FASTMCP_OIDC_CONFIG_URL`: URL of your OAuth provider's OIDC configuration (e.g., `https://your-tenant.us.auth0.com/.well-known/openid-configuration`)
- `FASTMCP_OIDC_CLIENT_ID`: Client ID from your registered OAuth application
- `FASTMCP_OIDC_CLIENT_SECRET`: Client secret from your registered OAuth application
- `FASTMCP_OIDC_BASE_URL`: Public URL of your FastMCP server (e.g., `https://your-server.com`)
- `FASTMCP_OIDC_AUDIENCE`: (Optional) Audience parameter if required by your provider

When enabled, the server will manage OAuth client registration and token validation using the `OIDCProxy` provider.

### JWT Token Verification (Alternative)

If you only need to validate Bearer tokens without a full OAuth flow:

- `FASTMCP_AUTH_TYPE=jwt`
- `FASTMCP_JWT_JWKS_URI`: URL to the JWKS endpoint (e.g., `https://your-tenant.us.auth0.com/.well-known/jwks.json`)
- `FASTMCP_JWT_ISSUER`: The expected issuer (`iss` claim)
- `FASTMCP_JWT_AUDIENCE`: (Optional) The expected audience (`aud` claim)

## Deployment Procedures

### 1. Docker (Recommended for production/remote)

#### Build the image
```bash
docker build -t mcp-postgres-server .
```

#### Run with Docker Compose (Easier local management)
Create a `.env` file or set variables in your shell, then:
```bash
docker-compose up -d
```

#### Run with Docker directly
```bash
docker run --rm \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://mcp_readonly:change_me@your_db_host:5432/your_db" \
  --name mcp-postgres \
  mcp-postgres-server
```

### 2. UV (Recommended for local Python development)
If you have [uv](https://github.com/astral-sh/uv) installed:

```bash
# Run the server directly
uv run mcp-postgres
```

Or using `uvx` (ephemeral run):
```bash
uvx --from . mcp-postgres
```

### 3. NPX (For Node.js users)
You can run the server using `npx` from the project root:

```bash
npx .
```
*(Note: Requires Python 3.12+ to be installed on your system)*

### 4. Cloud Deployment (Azure & AWS)

Infrastructure templates are provided in the `deploy/` directory.

#### Azure Container Apps (ACA)
Using the Azure CLI:
```bash
# Login and set your subscription
az login

# Create a resource group
az group create --name mcp-postgres-rg --location eastus

# Deploy using the Bicep template
az deployment group create \
  --resource-group mcp-postgres-rg \
  --template-file deploy/azure-aca.bicep \
  --parameters \
    containerImage="your-registry.azurecr.io/mcp-postgres:latest" \
    databaseUrl="your-db-url"
```

#### AWS ECS Fargate
Using the AWS CLI:
```bash
# Deploy the CloudFormation stack
aws cloudformation create-stack \
  --stack-name mcp-postgres-stack \
  --template-body file://deploy/aws-ecs.yaml \
  --capabilities CAPABILITY_IAM \
  --parameters \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxxx \
    ParameterKey=SubnetIds,ParameterValue=subnet-xxxx\,subnet-yyyy \
    ParameterKey=ContainerImage,ParameterValue=xxxx.dkr.ecr.us-east-1.amazonaws.com/mcp-postgres:latest \
    ParameterKey=DatabaseUrl,ParameterValue="your-db-url"
```

### 5. Verification
- Health: `http://localhost:8000/health` should return `ok`.
- MCP endpoint: `http://localhost:8000/mcp`.

### 6. Accessing the Remote Server (Azure)

Once deployed to Azure Container Apps, the server will be available over HTTPS.

#### Get the URL
You can find the URL (FQDN) in the Azure Portal under the **Overview** tab of your Container App, or via CLI:
```bash
az containerapp show \
  --name mcp-postgres-server \
  --resource-group mcp-postgres-rg \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

The full MCP endpoint will be:
`https://<your-fqdn>/mcp`

#### Configure your client
In your MCP client (e.g., Codex `config.toml`), use the HTTPS URL:
```toml
[mcp_servers.azure_postgres]
url = "https://mcp-postgres-server.your-id.region.azurecontainerapps.io/mcp"
enabled = true
# If you enabled authentication (OIDC/JWT), provide the token
bearer_token_env_var = "AZURE_MCP_TOKEN"
```

### Docker Health Checks

The provided `Dockerfile` includes a built-in health check that monitors the `/health` endpoint. When running in environments like Docker Compose or Kubernetes, the container status will automatically reflect the health of the MCP server.

## VS Code Setup

To use this server from VS Code, you need a VS Code extension that supports MCP servers over Streamable HTTP. 

### 1. Codex – OpenAI’s coding agent

Codex reads MCP servers from `~/.codex/config.toml`. 

#### For Local Deployment
```toml
[mcp_servers.postgres_local]
url = "http://localhost:8000/mcp"
enabled = true
```

#### For Azure Deployment (Remote)
1. Get your Azure FQDN (see [Accessing the Remote Server (Azure)](#6-accessing-the-remote-server-azure)).
2. Add to `config.toml`:
```toml
[mcp_servers.postgres_azure]
url = "https://your-app.region.azurecontainerapps.io/mcp"
enabled = true
# If authentication is enabled, provide the token via an environment variable
bearer_token_env_var = "AZURE_MCP_TOKEN"
```

### 2. Other VS Code Extensions
If you are using other extensions (like Cursor or generic MCP clients), look for "MCP Servers" in settings and add:
- **Type**: HTTP / Streamable HTTP
- **URL**: `https://your-app.region.azurecontainerapps.io/mcp`
- **Auth**: Add `Authorization: Bearer <your-token>` header if required.

## PostgreSQL Role Recommendations

### Read-only role (recommended for production)

Create a dedicated role that can only read data and catalog views. Example (adjust DB and schema names):

```sql
CREATE ROLE mcp_readonly LOGIN PASSWORD 'change_me_strong_password';
GRANT CONNECT ON DATABASE your_db TO mcp_readonly;

\\c your_db

GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO mcp_readonly;
```

### Maintenance role (use carefully)

If you want a write-enabled MCP server, use a separate role and keep it off production unless you have strong operational controls.

## Troubleshooting

### Codex can’t see the MCP server

- Confirm the container is running and port is mapped:
  - MCP endpoint: `http://localhost:8000/mcp`
  - Health: `http://localhost:8000/health`
- Confirm `~/.codex/config.toml` has the server entry under `[mcp_servers.<name>]`.
- Restart the Codex panel after editing the config.

### Server fails to start: missing DATABASE_URL

The server requires either:

- `DATABASE_URL`, or
- `PGHOST` + `PGUSER` + `PGDATABASE` (and optionally `PGPASSWORD`, `PGPORT`)

### PostgreSQL connection errors

- Verify the DB host is reachable from inside the container network.
- If using a managed database, ensure inbound rules allow the container host.
- Confirm credentials and database name in `DATABASE_URL`.

### `top_queries` returns “pg_stat_statements is not available”

`pg_stat_statements` requires Postgres configuration and extension setup:

1. Set `shared_preload_libraries = 'pg_stat_statements'` and restart Postgres
2. In the target database:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### Local pip install fails with TLS CA bundle error (Windows)

Use `python pipw.py install -r requirements.txt`, which repairs common cases where `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` point to a missing file for that process. If it still fails, use Docker-based deployment or repair your Python/pip certificate configuration.

## Security & Scalability Best Practices

### Security Hardening
- **Least Privilege**: Always use a read-only PostgreSQL role for `mcp_readonly` (see [PostgreSQL Role Recommendations](#postgresql-role-recommendations)).
- **Authentication**: Enable OIDC or JWT verification for remote endpoints.
- **Network Isolation**: Run the MCP server in a private network, exposing it only via an authenticated reverse proxy (e.g., Caddy, Nginx).
- **Statement Timeouts**: Keep `MCP_STATEMENT_TIMEOUT_MS` low (e.g., 30s) to prevent resource exhaustion from complex queries.

### Scalability Tuning
- **Connection Pooling**: Tune `MCP_POOL_MAX_SIZE` based on your expected concurrency and DB capacity.
- **Row Limits**: Use `MCP_MAX_ROWS` to prevent large result sets from consuming excessive memory in the MCP server or client.
- **Monitoring**: Check logs for "BLOCKED write attempt" warnings to identify unauthorized usage patterns.

## FAQ

### Should I use OAuth (OIDC) or JWT verification?

- Use OAuth (OIDC) if you want the server to participate in an interactive OAuth login/consent flow.
- Use JWT verification if you already have a separate system issuing Bearer tokens and you only need this server to validate them.

### Why does `db_locks` return an empty list?

`db_locks` only returns sessions that are actively blocked on locks and the sessions that are blocking them. If nothing is currently waiting on a lock, it returns `[]`.

### How do I run this over HTTPS?

Terminate TLS in front of the server (Caddy/Nginx/Traefik/Cloudflare) and reverse proxy to `http://localhost:8000`. The MCP endpoint becomes `https://your-domain/mcp`.

### How do I change the maximum rows returned by `run_query`?

Set `MCP_MAX_ROWS` or pass `max_rows` when calling `run_query`.

## Enhancements / Suggestions

- Add per-tool authorization (scopes/roles) and tool allowlists by environment.
- Add optional query redaction for `pg_stat_activity` output.
- Add health checks for database connectivity and pool status.
- Add additional DBA tools (bloat, vacuum progress, replication status, long transactions).
- Add structured tests and a CI workflow (lint/typecheck, container build, smoke tests).

