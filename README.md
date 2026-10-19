# Expense MCP Server

A personal expense ledger exposed as eight Model Context Protocol (MCP) tools. Local clients use STDIO. Hosted clients use authenticated Streamable HTTP and PostgreSQL.

The server uses MCP Python SDK 2.3.0, which supports the 2026-07-28 protocol revision and earlier clients. Its HTTP resource server requires OAuth before any MCP request reaches a tool.

## Supported tools

- `add_expense`
- `list_expenses`
- `update_expense`
- `delete_expense`
- `search_expenses`
- `monthly_summary`
- `category_summary`
- `top_merchants`

The server keeps each authenticated HTTP user's ledger separate using a SHA-256 hash of the verified issuer and subject. Reads require `expenses:read`; writes require both `expenses:read` and `expenses:write`. User identity is never accepted as a tool argument. When the OAuth settings are missing, the HTTP service can start for its database health check but the MCP route returns `503`; partial OAuth settings fail startup. SSE is disabled.

## Local STDIO with PostgreSQL

The included Compose file starts a local PostgreSQL 16 database only. Its development password is fixed and the database port is bound to loopback; do not expose this setup to a network.

1. Install Python 3.11 and Docker Desktop.
2. Start PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

3. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` if you do not already have a local `.env`. The example connects to the Compose PostgreSQL database and uses STDIO. Keep `.env` private.
5. Run `python run.py`, or configure your MCP client to launch that command as a local STDIO server.

For lightweight local experiments, SQLite is supported when `APP_ENV` is not `production`. SQLite does not enforce fixed decimal precision at the database layer; tool inputs are validated by the application. Production startup rejects SQLite.

## Authenticated Streamable HTTP

HTTP requires an external OpenID Connect/OAuth provider that issues signed JWT access tokens. This project verifies tokens; it does not create users, issue tokens, or manage provider accounts. Set these environment variables in the server runtime:

| Variable | Purpose |
|---|---|
| `OAUTH_ISSUER_URL` | Exact issuer URL expected in the token's `iss` claim. |
| `OAUTH_JWKS_URL` | HTTPS URL for the issuer's public signing keys. |
| `OAUTH_AUDIENCE` | Expected token audience. |
| `OAUTH_RESOURCE_URL` | Public MCP URL ending in `/mcp`. |
| `OAUTH_JWT_ALGORITHM` | Optional asymmetric algorithm; defaults to `RS256`. Supported: `RS256`, `RS384`, `RS512`, `ES256`, `ES384`. |

Tokens must have valid signatures and include `exp`, `iss`, `sub`, `aud`, and a `scope` or `scp` claim. They must carry `expenses:read`; mutations also require `expenses:write`. The verifier uses the configured JWKS, issuer, audience, and algorithm, with a short network timeout and cached signing keys. Production issuer, JWKS, and resource URLs must use HTTPS. Loopback HTTP is allowed only outside production.

The `/health` route is public for hosting-platform health checks and returns 503 when PostgreSQL is unavailable. If no OAuth settings are configured, `/mcp` returns 503 so Render can replace an older revision without opening an unauthenticated MCP endpoint. Once OAuth is configured, the MCP endpoint and its tools require a valid token. Do not use a hosted MCP endpoint until the provider has been configured and the HTTP auth flow has been tested with real credentials.

## PostgreSQL and schema migration

PostgreSQL is required when `APP_ENV=production`; there is no SQLite fallback. The application checks database connectivity before serving requests, applies a migration to existing `expenses` tables, creates missing tables, and ensures an owner index exists. Legacy amounts are rounded to the supported currency precision during migration (zero fractional digits for JPY, two for other supported currencies); blank currency values become INR and existing currency codes are trimmed and uppercased. Migration stops without truncating currency values longer than three characters or accepting NULL amounts, categories, or dates. Back up existing data before deploying this migration.

For Render, the Blueprint creates a free PostgreSQL database for demos. Render's free databases expire after 30 days and do not include backups, so do not store expense data you need to retain there. Upgrade the database plan before using it for ongoing data.

The Blueprint declares `OAUTH_ISSUER_URL`, `OAUTH_JWKS_URL`, `OAUTH_AUDIENCE`, and `OAUTH_RESOURCE_URL` as operator-supplied values. This repository does not contain identity-provider credentials. On an existing Blueprint-managed service, Render does not prompt again for newly added `sync: false` variables during a later Blueprint sync; add these values manually on the service's Environment page, then save and deploy. See [Render's Blueprint environment-variable behavior](https://render.com/docs/blueprint-spec#setting-environment-variables).

For `OAUTH_RESOURCE_URL`, use the public Render service URL with `/mcp` appended. The issuer must exactly match the token's `iss` claim, the JWKS URL must be the issuer's signing-key endpoint, and the audience must match the access tokens issued for this MCP server. Grant `expenses:read` for reads and `expenses:write` for mutations. Do not guess these values or copy them from another identity provider.

For a step-by-step Auth0 setup that maps the provider values to this Render service, see [`AUTH0_RENDER_SETUP.md`](AUTH0_RENDER_SETUP.md).

After deployment, verify the protected-resource metadata at `/.well-known/oauth-protected-resource/mcp`, then send an MCP `initialize` request to `/mcp` without a bearer token and confirm it returns `401`. A successful `/health` response alone proves only that PostgreSQL is reachable; it does not prove the MCP endpoint is protected. Until these checks pass, do not use a hosted endpoint for expense data. If a previously deployed revision remains active after a failed deploy, suspend that Render web service until OAuth is configured and the authenticated flow is verified.

## Validation

Run the unit suite with:

```bash
python -m pytest -q
```

PostgreSQL migration tests run when `TEST_POSTGRES_URL` points to a disposable test database. The GitHub Actions workflow provisions PostgreSQL and runs both the suite and startup checks on pushes and pull requests.

## Agent skill package

[`skills/expense-tracker-mcp-companion/SKILL.md`](skills/expense-tracker-mcp-companion/SKILL.md) contains the companion instructions for compatible agents. The skill requires this MCP server to be installed and connected separately; it does not include or host the server or its database. Use a private local STDIO connection for personal ledgers unless hosted OAuth authentication has been configured and verified.

## License

No license file is included. The repository does not grant permission to redistribute the server source.
