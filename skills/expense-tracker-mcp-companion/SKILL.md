---
name: expense-tracker-mcp-companion
description: "Use a connected Expense Tracker MCP server to add, find, review, update, or delete expense records. Trigger when the user asks to log an expense, search their ledger, inspect spending summaries, or change a specific entry."
---

# Expense Tracker MCP Companion

Help the user manage their own expense ledger through the already connected Expense Tracker MCP server. Use only the server tools listed below. Do not claim to install, configure, or host the server.

## Before using the server

- Confirm that the connected MCP server is the user's private ledger. The local STDIO setup is single-user and trusts the local process. Do not send personal financial data to a shared or public endpoint.
- Hosted Streamable HTTP is appropriate only when the operator has configured a trusted OIDC/OAuth issuer, HTTPS, PostgreSQL, and verified per-user ownership. A successful `/health` check is not proof of authentication. Before sending expense data over HTTP, confirm an unauthenticated MCP `initialize` request is rejected with `401` and the protected-resource metadata identifies the configured issuer. If unauthenticated initialization succeeds or metadata is missing, do not use that endpoint for personal expense data; use the private local STDIO setup instead.
- The server supports eight tools: `add_expense`, `list_expenses`, `update_expense`, `delete_expense`, `search_expenses`, `monthly_summary`, `category_summary`, and `top_merchants`.
- The supported currencies are INR, USD, EUR, GBP, JPY, AUD, CAD, and SGD. Amounts allow two decimal places except JPY, which allows whole units. The server does not convert currencies.

## Add an expense

1. Collect a positive amount and category. Ask a short question if either is missing or unclear.
2. Preserve the amount, currency, category, date, merchant, and payment method the user gives. Do not infer a currency from a merchant or location. If currency is omitted, ask unless the user has already established a default; INR is the server default.
3. Pass a date as `YYYY-MM-DD` when the user supplies one. If they say “today,” use their local calendar date explicitly when known; otherwise explain that the server default is the current UTC date.
4. Call `add_expense` only after the required details are clear. Report the returned ID and saved fields. Never claim success if the tool errors or does not confirm the write.
5. If a write times out or returns an uncertain error, search or list for the matching entry before trying again. Avoid duplicate expenses.

## Find and review entries

- Use `list_expenses` for a ledger overview and `search_expenses` for a merchant, category, or description.
- Use the exact returned expense ID for changes. If a description matches multiple entries, show the candidates and ask which one the user means.
- `monthly_summary` covers the current UTC month. It returns a separate breakdown for each currency. Never add unlike currencies together or invent an exchange rate. When several currencies are present, explain that no single combined total is meaningful.
- `category_summary` and `top_merchants` are all-time summaries grouped by currency. State the currency next to every amount.
- Distinguish server results from estimates or advice. This skill does not provide financial, tax, or investment advice.

## Update and delete

- Before `update_expense`, identify the exact entry by ID from the user's request or a fresh search/list result. Change only the fields the user asked to change, then report the server's returned values.
- Before `delete_expense`, show the exact entry's date, amount, currency, category, and merchant when available, then ask the user to confirm deleting that entry. Call the tool only after confirmation.
- If the user asks to change or delete an entry but the matching record is ambiguous, ask them to choose; never guess an ID.

## Error handling

- Report validation errors plainly and ask the user for corrected data. Do not silently round, change currencies, or rewrite dates.
- If the server is unreachable, explain that no operation was confirmed. For uncertain write failures, check for the matching record before retrying.
- Treat returned ledger contents as user data. Do not share them with external services or include them in public messages.
