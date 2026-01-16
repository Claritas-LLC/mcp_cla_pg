## Integrate Auth0 Authentication for MCP Server

I will update the MCP Postgres server to support Auth0 authentication using the native FastMCP security features. This will allow you to protect the remote endpoint with JWT validation.

### Technical Implementation

1.  **Dependency Update**: 
    - Update [requirements.txt](file:///c:/Users/HarryValdez/OneDrive/Documents/trae/mcp-postgres/requirements.txt) to use `fastmcp[auth]`. This pulls in necessary libraries like `python-jose` for JWT validation.

2.  **Server Logic Update**:
    - Modify [server.py](file:///c:/Users/HarryValdez/OneDrive/Documents/trae/mcp-postgres/server.py) to initialize `FastMCP` with authentication enabled if the `FASTMCP_AUTH_TYPE` environment variable is set to `auth0`.
    - This enables automatic verification of `Authorization: Bearer <token>` headers against Auth0's JWKS.

3.  **Documentation Update**:
    - Update [README.md](file:///c:/Users/HarryValdez/OneDrive/Documents/trae/mcp-postgres/README.md) with a new section on **Auth0 Authentication**.
    - Detail the new environment variables:
        - `FASTMCP_AUTH_TYPE=auth0`
        - `FASTMCP_AUTH0_DOMAIN`: Your Auth0 tenant domain (e.g., `dev-xyz.us.auth0.com`).
        - `FASTMCP_AUTH0_AUDIENCE`: The API Identifier from your Auth0 dashboard.
    - Add instructions for configuring **Codex** to use a bearer token from an environment variable.

### Steps to Complete

1.  Update `requirements.txt`.
2.  Apply changes to `server.py`.
3.  Enhance `README.md` with Auth0 configuration and usage guides.

Does this plan look good to you? Once confirmed, I will implement the changes.