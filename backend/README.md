# NewsieAI Backend

Backend services for NewsieAI: FastAPI API, multi-agent orchestration, MCP tool servers, scheduler-driven thread execution, SQLite persistence, and Solana/x402 payment flow.

## Current Architecture

- `api_server.py` is the main backend entrypoint.
- Threads are saved and scheduled via `thread.py` + `scheduler_config.py`.
- Execution runtime is in `task.py`:
  - `raw` mode uses engine functions directly.
  - `smart` mode routes retrieval through `agents/retriv.py`.
- Agents call MCP tools in `tools/` (search, payment, profile manager).
- Retrieved items and app data are persisted in `data/newsieai.db`.

## Current Backend Structure

```text
backend/
  api_server.py                 # Main FastAPI server (auth, profile, workflows, threads, news, DB ops)
  database.py                   # SQLite schema and data access
  auth.py                       # JWT auth and token helpers
  task.py                       # Thread block execution runtime
  thread.py                     # Scheduler job wiring for interval/daily jobs
  scheduler_config.py           # APScheduler + SQLAlchemy job store config
  main.py                       # Local interactive test runner (legacy/dev utility)
  API_README.md                 # API-focused notes
  requirements_api.txt          # API dependency subset

  agents/
    retriv.py                   # Smart retrieval agent (MCP search tool integration)
    profile_manager.py          # Interactive profile manager agent
    accountant.py               # Payment decision + Solana payment orchestration
    personal_assistant.py       # Time/place-aware orchestration over retrieval

  engine/
    x_from_user.py              # Raw X user retrieval block
    x_from_topic.py             # Raw X topic retrieval block
    general_search.py           # General search block placeholder (not fully implemented)

  tools/
    start_mcp.py               # Starts MCP services (search/pay/profile_manager)
    retrival_tools.py          # MCP search tools (Twitter advanced search, etc.)
    tool_pay.py                # MCP payment tools (pay_solana, reaccess_payed_content)
    profile_manager_tool.py    # MCP profile description CRUD tools
    geo_server.py              # MCP geo/time tool (optional standalone)
    sources.py                 # Source adapters (Alpha Vantage, paid endpoint wrapper)
    walletx.py                 # Wallet payment helper wrapper

  wallet/
    wallet.py                  # Solana wallet handling and transfers

  data/
    newsieai.db                # SQLite database files

  datalog/
    request.txt                # Request logs
    transfer_log.txt           # Payment transfer logs
    news_*.txt                 # Generated news logs

  test_server.py               # x402-like payment-required content server
  test_x402_flow.py            # End-to-end payment flow test script
  generate_a_wallet.py         # Utility to generate wallet keys
```

## Quick Start

### 1. Install dependencies

From project root:

```bash
pip install -r backend/requirements_api.txt
pip install langchain langchain-openai langchain-mcp-adapters fastmcp python-dotenv requests httpx pytz apscheduler sqlalchemy solana solders
```

### 2. Configure `.env`

Create/update `.env` in project root with at least:

```env
# LLM
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini

# Search / social
TWITTER_API_KEY=your_twitterapi_io_key
BASE_URL=https://api.twitterapi.io/twitter/tweet/advanced_search
ALPHAADVANTAGE_API_KEY=your_alpha_vantage_key

# MCP ports
SEARCH_HTTP_PORT=8001
PAY_HTTP_PORT=8007
PROFILE_MANAGER_HTTP_PORT=8009
DATE_TIME_HTTP_PORT=8002
DATE_TIME_HTTP=8002

# Auth / DB
JWT_SECRET_KEY=replace_this_in_prod
DATABASE_PATH=backend/data/newsieai.db

# Solana (sender wallet used by wallet tools)
SOLANA_PUBKEY=your_sender_pubkey
SOLANA_SECRETKEY=your_sender_secret_base58

# Solana (receiver wallet used by x402 test server)
SERVER_PUBKEY=your_server_pubkey
SERVER_SECRETKEY=your_server_secret_base58
```

### 3. Start MCP services

```bash
python backend/tools/start_mcp.py
```

Starts:
- Search MCP (`retrival_tools.py`)
- Pay MCP (`tool_pay.py`)
- Profile Manager MCP (`profile_manager_tool.py`)

### 4. Start API server

```bash
python backend/api_server.py
```

Default API URL: `http://localhost:8008`

### 5. Optional: test x402 payment flow

Terminal A:

```bash
python backend/test_server.py
```

Terminal B:

```bash
python backend/test_x402_flow.py
```

## Runtime Flow (Current)

1. Frontend saves/starts a thread via `/api/thread/*`.
2. Scheduler triggers `execute_periodic_scan(...)` in `task.py`.
3. Each thread block runs in:
   - `raw`: engine-level logic (`x_from_user`, `x_from_topic`, `general_search` placeholder)
   - `smart`: `agents/retriv.py` for tool-driven retrieval/filtering
4. Retrieved items are normalized and stored in DB.
5. If paid content is encountered, accountant/payment MCP path can execute Solana payment and re-access content.

## API Surface (High Level)

Main endpoint groups in `api_server.py`:

- Auth: `/api/auth/*`
- Profile: `/api/profile*`, `/api/profile/chat`
- Workflows: `/api/workflow/*`
- Threads: `/api/thread/*`
- News items: `/api/news/*`
- DB ops: `/api/db/*`

For endpoint payload examples, see `backend/API_README.md`.

## Notes on Current Scope

- Strongest support today is X-platform retrieval and thread-based orchestration.
- `general-search` engine path is still placeholder logic in `engine/general_search.py`.
- Payment and prompt-safety hardening are active improvement areas.
