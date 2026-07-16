# 💸 Expense MCP Server

A production-ready **Model Context Protocol (MCP) server** for managing personal expenses — built with FastMCP, SQLAlchemy, and Pydantic. Deploys as a Docker container on Render with PostgreSQL, and connects to Claude Desktop, Cursor, VS Code, or any MCP-compatible client.

---

## Status

✅ **Live on Render** — Docker · PostgreSQL · Streamable HTTP

| | |
|---|---|
| **Transport** | Streamable HTTP |
| **Database** | PostgreSQL (Render managed) |
| **Health endpoint** | `/health` |
| **MCP endpoint** | `/mcp` |

---

## Architecture

```
Claude Desktop / Cursor / VS Code MCP
            │
            │  MCP over Streamable HTTP
            ▼
   ┌─────────────────────┐
   │  Expense MCP Server │  Docker · Render
   │  FastMCP + Uvicorn  │
   └────────┬────────────┘
            │
            ▼
   ┌─────────────────────┐
   │   Expense Service   │  Business logic
   └────────┬────────────┘
            │
            ▼
   ┌─────────────────────┐
   │     Repository      │  Data access layer
   └────────┬────────────┘
            │
            ▼
   ┌─────────────────────┐
   │  SQLAlchemy ORM     │
   └────────┬────────────┘
            │
            ▼
   ┌─────────────────────┐
   │  PostgreSQL / SQLite│  Prod / Dev
   └─────────────────────┘
```

### API Request Flow

```
Claude  →  MCP Tool  →  FastMCP  →  Expense Service  →  Repository  →  SQLAlchemy  →  PostgreSQL
```

---

## ✨ Features

- **8 MCP Tools** — add, list, update, delete, search expenses, and get monthly/category/merchant summaries
- **Dual transport** — STDIO (local Claude Desktop) and Streamable HTTP (remote/Docker/Render)
- **Dual database** — SQLite for local development, PostgreSQL for production
- **Production-ready** — structured logging, custom exceptions, connection pooling, non-root Docker user
- **31 tests** — full repository, service, and tool coverage with in-memory SQLite isolation
- **One-command deploy** — `render.yaml` Blueprint auto-provisions PostgreSQL + Docker web service

### Production Features

| Feature | Detail |
|---|---|
| ✓ Docker multi-stage image | Minimal, hardened runtime layer |
| ✓ PostgreSQL | Render-managed with connection pooling |
| ✓ Render Blueprint | Auto-provisions all infrastructure |
| ✓ Health endpoint | `/health` for Render and load balancer checks |
| ✓ Remote HTTP MCP | Accessible at `/mcp` from any MCP client |
| ✓ Connection pooling | `pool_size=5`, `max_overflow=10`, `pool_recycle=1800` |
| ✓ Structured logging | ISO timestamps, log levels, logger names |
| ✓ Non-root container | `appuser` with no escalation |
| ✓ Automatic DB provisioning | Tables created on first startup |

---

## Compatible Clients

✅ Claude Desktop  
✅ Cursor  
✅ VS Code MCP extension  
✅ Any MCP client supporting Streamable HTTP

---

## Transport Modes

| Transport | When to use |
|---|---|
| `stdio` | Local Claude Desktop — server runs as a child process |
| `streamable-http` | Remote deployment, Docker, Render — server listens on HTTP |

---

## 🗂 Project Structure

```
expense-mcp-server/
├── app/
│   ├── config.py              # Pydantic Settings (reads from .env)
│   ├── exceptions.py          # ExpenseNotFoundError, ExpenseValidationError
│   ├── logging_config.py      # Structured logging setup
│   ├── mcp_instance.py        # FastMCP instance + /health endpoint
│   ├── server.py              # Registers all 8 tools
│   ├── database/
│   │   ├── db.py              # Engine, SessionLocal, validate_connection()
│   │   └── models.py          # Expense SQLAlchemy model
│   ├── schemas/
│   │   └── expense.py         # ExpenseCreate, ExpenseUpdate (Pydantic)
│   ├── repositories/
│   │   └── expense_repository.py
│   ├── services/
│   │   └── expense_service.py
│   ├── tools/
│   │   ├── add_expense.py
│   │   ├── list_expenses.py
│   │   ├── update_expense.py
│   │   ├── delete_expense.py
│   │   ├── search_expenses.py
│   │   ├── monthly_summary.py
│   │   ├── category_summary.py
│   │   └── top_merchants.py
│   └── utils/
│       ├── dates.py
│       └── currency.py
├── tests/
│   ├── conftest.py            # In-memory SQLite fixtures + monkeypatch
│   └── test_expense.py        # 31 tests
├── run.py                     # Entry point
├── requirements.txt
├── Dockerfile                 # Multi-stage Docker build
├── docker-compose.yml         # App + PostgreSQL local stack
├── render.yaml                # Render Blueprint (PostgreSQL + Docker web service)
└── .env                       # Local environment variables
```

---

## 🛠 MCP Tools

| Tool | Description |
|---|---|
| `add_expense` | Add a new expense with amount, category, date, merchant, currency |
| `list_expenses` | List all expenses sorted by date descending |
| `update_expense` | Update any field of an existing expense by ID |
| `delete_expense` | Delete an expense by ID |
| `search_expenses` | Search by category, description, or merchant |
| `monthly_summary` | Total, count, average, and max for the current month |
| `category_summary` | Spending totals grouped by category |
| `top_merchants` | Top merchants by total spending |

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
| `MCP_SERVER_NAME` | `Expense Tracker` | Name shown in Claude Desktop |
| `TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `HOST` | `0.0.0.0` | Bind host (HTTP mode only) |
| `PORT` | `8000` | Bind port for local/Docker. **Render injects `PORT=10000` automatically — no manual configuration needed.** |
| `DATABASE_URL` | `sqlite:///./expenses.db` | SQLite or PostgreSQL connection string |

---

## 🚀 Getting Started

### Option A — Local Development (STDIO + SQLite)

**1. Clone and create a virtual environment**

```bash
git clone https://github.com/your-username/expense-mcp-server.git
cd expense-mcp-server
python -m venv .venv
```

**2. Activate the virtual environment**

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure `.env`**

```env
APP_ENV=development
LOG_LEVEL=INFO
MCP_SERVER_NAME=Expense Tracker
TRANSPORT=stdio
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./expenses.db
```

**5. Run the server**

```bash
python run.py
```

The server starts in STDIO mode — ready to be used with Claude Desktop.

---

### Option B — Local Docker + PostgreSQL (HTTP)

**1. Start the full stack**

```bash
docker-compose up --build
```

This starts:
- `expense_postgres` — PostgreSQL 16 on port 5432
- `expense_mcp` — MCP server on port 8000 (Streamable HTTP transport)

The app waits for PostgreSQL to pass its health check before starting.

**2. Verify it's running**

```bash
curl http://localhost:8000/health
```

---

### Option C — Deploy to Render (Docker + PostgreSQL)

The project deploys as a **Docker multi-stage image** on Render.

**1. Push your repo to GitHub**

**2. Go to [render.com](https://render.com) → New → Blueprint**

**3. Connect your GitHub repo** — Render auto-detects `render.yaml` and automatically creates:
- A **managed PostgreSQL database**
- A **Docker web service** running `run.py`
- All required **environment variables**
- **Database connection** wired via `fromDatabase.connectionString`

**4. Your server will be live at:**
```
https://<your-render-service>.onrender.com
```

> Replace `<your-render-service>` with your actual Render service name (shown in the dashboard after deployment).

---

## 🔍 Health Check

The server exposes `/health` for Render and load balancer health checks.

```bash
curl https://<your-render-service>.onrender.com/health
```

**Response:**
```json
{"status": "ok"}
```

---

## 🔌 Verify the MCP Endpoint

```
GET https://<your-render-service>.onrender.com/mcp
```

> **Note:** A browser will show `405 Method Not Allowed`. This is expected — `/mcp` speaks the MCP protocol (not plain HTTP GET). Use an MCP client to connect.

---

## 🖥 Claude Desktop Configuration

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or  
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

### Option A — Local STDIO

```json
{
  "mcpServers": {
    "expense-tracker": {
      "command": "C:\\path\\to\\expense-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\expense-mcp-server\\run.py"]
    }
  }
}
```

### Option B — Render (Remote HTTP)

```json
{
  "mcpServers": {
    "expense-tracker": {
      "type": "streamable-http",
      "url": "https://<your-render-service>.onrender.com/mcp"
    }
  }
}
```

### Option C — Docker (Local HTTP)

```json
{
  "mcpServers": {
    "expense-tracker": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

> You can include all three entries simultaneously — just give each a unique key.

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

Expected output:

```
31 passed in ~1s
```

The test suite covers:
- `TestExpenseRepository` — 13 tests (CRUD + search + summaries)
- `TestExpenseService` — 10 tests (business logic + error handling)
- `TestTools` — 8 tests (MCP tool integration)

Tests use an **in-memory SQLite database** with full transaction rollback isolation between each test.

---

## 🗃 Database

### SQLite (Local)

Zero configuration. The `expenses.db` file is created automatically on first run.

```env
DATABASE_URL=sqlite:///./expenses.db
```

### PostgreSQL (Docker / Production)

```env
DATABASE_URL=postgresql://expense_user:expense_pass@localhost:5432/expense_db
```

The `Expense` table is created automatically via `Base.metadata.create_all()` on startup.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `amount` | Float | Required, must be > 0 |
| `category` | String | Required |
| `description` | String | Optional |
| `merchant` | String | Optional |
| `payment_method` | String | Optional |
| `currency` | String | Default: `INR` |
| `expense_date` | Date | Required |
| `created_at` | DateTime | Auto-set to UTC now |

---

## 📦 Tech Stack

| Layer | Library | Version |
|---|---|---|
| MCP Framework | `mcp` (FastMCP) | 1.28.1 |
| Settings | `pydantic-settings` | 2.14.2 |
| ORM | `SQLAlchemy` | 2.0.51 |
| Validation | `pydantic` | 2.13.4 |
| PostgreSQL driver | `psycopg2-binary` | 2.9.10 |
| HTTP server | `uvicorn` + `starlette` | — |
| Testing | `pytest` | 9.1.1 |

---

## 📄 License

MIT
