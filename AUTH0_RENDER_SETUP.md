# Auth0 setup for the Render demo

This guide configures the existing hosted Expense MCP service to use Auth0 for user sign-in and JWT access tokens. Auth0 issues and validates identities; the MCP server validates each token and keeps each user's expenses in a separate PostgreSQL ledger.

## Before you start

- Create an Auth0 account and a development tenant under your own account. Auth0 currently lists a $0 Free plan with up to 25,000 monthly active users; check its current terms before relying on that limit.
- Do not send or commit passwords, client secrets, API keys, or access tokens. The MCP server needs only the public issuer, JWKS endpoint, API audience, and its own public resource URL.
- Suspend the Render web service until OAuth is configured. As checked on 2026-10-19, the current public revision returns `200` to an unauthenticated MCP `initialize` request and returns `404` for the protected-resource metadata route.

## 1. Create the Auth0 API

In the Auth0 Dashboard, open **Applications > APIs > Create API**.

Use these settings:

- **Name:** Expense MCP Server
- **Identifier:** `https://expense-mcp-server-awxq.onrender.com/mcp`
- **Signing Algorithm:** `RS256`

The Identifier is the API audience. It intentionally matches the public MCP resource URL: MCP clients send that URL in OAuth's `resource` parameter, and Auth0's Resource Parameter Compatibility Profile maps that parameter to the API audience.

Under the API's permissions/scopes, add exactly:

- `expenses:read`
- `expenses:write`

Enable RBAC for the API. Create a role such as **Expense Ledger Owner**, grant it both permissions, and assign that role to your Auth0 user. The server requires `expenses:read` for every HTTP request and additionally requires `expenses:write` for mutations. The access token must expose the granted scopes in its `scope` or `scp` claim; an Auth0 `permissions` claim by itself is not read by this server.

## 2. Enable resource parameter compatibility

In the Auth0 tenant settings, open **Settings > Advanced** and enable **Resource Parameter Compatibility Profile**. MCP clients use the standard OAuth `resource` parameter. Without this compatibility setting, Auth0 can issue a token with the wrong audience for this MCP API.

For an initial connection test, use a statically registered MCP client where available. Auth0's MCP Inspector instructions offer static registration for that test. Dynamic Client Registration (DCR) is open registration in Auth0 and lets unauthenticated callers create application registrations; it does not by itself grant access to expense data, but it can create tenant clutter. Enable DCR only if the MCP client you intend to use requires it and you accept that operational trade-off. The MCP specification is moving toward Client ID Metadata Documents, so test the actual target client instead of assuming every client follows the same registration path.

## 3. Copy the exact issuer and key URL

Replace `<tenant-domain>` with the public Auth0 tenant domain shown in the Dashboard, without `https://`.

Open `https://<tenant-domain>/.well-known/openid-configuration` and copy its `issuer` value exactly, including its trailing slash if present. The matching public signing-key URL is:

`https://<tenant-domain>/.well-known/jwks.json`

Do not use the Auth0 Management API audience or an ID token as the MCP audience/token. The MCP server expects a signed JWT access token for the API Identifier above.

## 4. Configure Render

The current public Render MCP URL is:

`https://expense-mcp-server-awxq.onrender.com/mcp`

In Render, open the `expense-mcp-server` web service, then **Environment**. Add or update these values:

| Key | Value |
|---|---|
| `OAUTH_ISSUER_URL` | Exact `issuer` copied from Auth0 discovery metadata |
| `OAUTH_JWKS_URL` | `https://<tenant-domain>/.well-known/jwks.json` |
| `OAUTH_AUDIENCE` | `https://expense-mcp-server-awxq.onrender.com/mcp` |
| `OAUTH_RESOURCE_URL` | `https://expense-mcp-server-awxq.onrender.com/mcp` |
| `OAUTH_JWT_ALGORITHM` | `RS256` |

Keep those values in Render, not in `render.yaml`, `.env.example`, the repository, or an Agensi skill package. This existing Blueprint uses `sync: false`; Render does not prompt for newly added values during later Blueprint syncs, so enter them manually on the service's Environment page. Save and deploy after all four required `OAUTH_*` values are present. If the public Render service URL changes, update the Auth0 API Identifier, `OAUTH_AUDIENCE`, and `OAUTH_RESOURCE_URL` together.

## 5. Verify before resuming public use

After the deployment completes, verify all of the following:

1. `GET /health` returns `200`. This only confirms the service can reach PostgreSQL.
2. `GET /.well-known/oauth-protected-resource/mcp` returns `200` and names the Auth0 issuer.
3. Send a valid MCP `initialize` request to `/mcp` with no bearer token and the required `Accept: application/json, text/event-stream` header. It must return `401` with a `WWW-Authenticate` challenge that points to the protected-resource metadata.
4. Connect using the intended MCP client and sign in through Auth0. Confirm it receives an access token whose `iss`, `aud`, expiration, and scopes match the configured values.
5. Confirm a read request works with `expenses:read`, a mutation without `expenses:write` is rejected, and separate Auth0 users cannot view one another's entries.

Only resume the Render service after the unauthenticated `initialize` is rejected and the authenticated client flow succeeds. The GitHub Actions workflow has passed unit/integration tests and production startup against PostgreSQL, but those results do not establish that the live Render/Auth0 flow is configured.

## References

- [Auth0 pricing](https://auth0.com/pricing)
- [Auth0: Test your MCP server with MCP Inspector](https://auth0.com/ai/docs/mcp/guides/test-your-mcp-server-with-mcp-inspector)
- [Auth0: MCP audience and resource parameter compatibility](https://support.auth0.com/center/s/article/mcp-audience-error-with-auth0)
- [Auth0: Create an API and set an API Identifier](https://auth0.com/docs/quickstart/backend/golang/interactive)
- [MCP: client registration changes](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [Render: environment variables and Blueprint `sync: false`](https://render.com/docs/blueprint-spec#setting-environment-variables)
- [Render: environment variable dashboard steps](https://render.com/docs/configure-environment-variables)
