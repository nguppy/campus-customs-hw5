# Campus Customs: Multi-Agent Operations (HW5)

A five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service) that works the Campus Customs shop's open tickets. The pieces:
- **Agents:** PydanticAI agents on `gpt-6-luna` via Portkey.
- **MCP server:** a FastMCP server, the only code that touches the shop database.
- **Backend:** a FastAPI backend.
- **Dashboard:** a React + Vite + TypeScript board where a human picks a ticket, watches the agents work, and approves payments.

The three tickets:
- **101:** a customer order for an out-of-stock tee
- **102:** a rent notice
- **103:** a bulk hoodie discount request

All three were resolved in the final run (see `output/`).

## What's in the repo

| Path | What it is |
|---|---|
| `data/campus_customs.db` | **Original** shop database. Never modified. |
| `data/campus_customs_new.db` | **Working copy** the agents use. Committed in its final, resolved state; reset it before a fresh run (below). |
| `mcp_server/server.py` | FastMCP server `campus-customs`: 14 tools, 7 read and 7 write (see `mcp_server/README.md`) |
| `.mcp.json` | MCP connection config. The backend resolves `python` to its own interpreter and the script path to this folder. |
| `backend/` | Agents (`boss.py`, `inventory.py`, `accounting.py`, `facilities.py`, `customer_service.py`), prompts (`prompts/`), data types (`models.py`), audit trail (`audit.py`), the team runner (`team.py`), and the FastAPI app (`main.py`) |
| `frontend/` | React dashboard |
| `output/` | Deliverables: `harness.md`, `desk_tickets.html`, `resolved_board.html`, `resolved_tickets.json`, `audit_trail.json`, `design.md`, `mcp_smoke.json`, `screenshots/` |
| `AI_prompts.md` | Log of every prompt used to build this, by problem |

## Setup (once)

You need Python 3.12+ (developed on 3.14), Node 20+, and a Portkey API key with access to `gpt-6-luna`.

```bash
# from the repo root
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && cd ..
```

Set the API key in your shell. It's read from the environment and is never stored in the repo; see `.env.example`.

```bash
# macOS/Linux
export PORTKEY_API_KEY=your-key
# Windows PowerShell
$env:PORTKEY_API_KEY = "your-key"
```

## Running it

Run each step from the repo root with the virtual environment active, unless the step says otherwise.

### 1. Clean run: copy the original DB over the working copy

The working copy is committed with the final, resolved results. To start clean, copy the original over it:

```bash
# macOS/Linux
cp data/campus_customs.db data/campus_customs_new.db
# Windows (PowerShell)
Copy-Item data\campus_customs.db data\campus_customs_new.db -Force
```

Once the backend is running, the same reset is available as `POST /reset` or the **Reset data** button on the board (see step 5).

### 2. Start the MCP server

```bash
python mcp_server/server.py
```

The server speaks MCP over stdio and talks only to `data/campus_customs_new.db`. **You usually don't need to start it by hand:** the agents and the backend launch it automatically from `.mcp.json` whenever they need it. Running it directly is a quick check that it starts, and MCP clients such as Claude Code can attach to it through `.mcp.json`.

### 3. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

- The backend serves **http://localhost:8000**. Interactive API docs are at http://localhost:8000/docs.
- `PORTKEY_API_KEY` must be set in this shell.
- On Windows, if `--reload` ever stalls after a code change, stop the server and start it again.

| Route | What it does |
|---|---|
| `GET /tickets` | The tickets and whether each is open or resolved |
| `POST /tickets/{id}/run` | Run the agent team on one ticket |
| `GET /events` | What each agent said and which tools it used (live) |
| `GET /approvals` | Payments, purchase orders and discounts waiting for a human |
| `POST /approvals/{id}/approve` | A human approves an item; this is the only thing that moves cash |
| `GET /cash` | Current checking balance |
| `POST /reset` | Reset the working DB to the original values |

### 4. Start the React board

```bash
cd frontend
npm run dev
```

This opens **http://localhost:5173** in your browser. The board calls the backend at `http://localhost:8000`; the backend only accepts browser requests from this page.
1. Pick a ticket and click **Start agent team**.
2. Watch the agents work live.
3. Approve payments when asked: type your name and click **Approve**.

### 5. Reset the DB before a full three-ticket run

Always start a full run of 101, 102 and 103 from the original data. Do one of these:
- Click **Reset data** in the board header.
- Call the reset route: `curl -X POST http://localhost:8000/reset`
- Use step 1 (copy the original DB) while the backend is stopped.

Then run each ticket from the board. Approve what the agents prepare, and run the ticket again if the Boss still has a step left. A ticket can take more than one run.

**Command-line alternative:** this resets the DB itself, then runs the open tickets in order:

```bash
python -m backend.team            # all open tickets
python -m backend.team 101 103    # specific tickets
```

Approvals still happen through the board or the approve route.

## Final run results (Problem 9)

| Ticket | Outcome | Cash |
|---|---|---|
| 101 | Invoice 501 paid ($840) so the vendor can ship; 1-tee restock ordered ($8); customer told the arrival date (2026-09-05) | −$848.00 |
| 102 | Rent paid ($2,400) | −$2,400.00 |
| 103 | 8 of 20 hoodies in stock; discount of $52 each approved (no cash moves); customer told about the shortfall | $0.00 |

Checking: **$3,400.00 → $152.00**, which matches `cash_accounts` in the working copy. Details are in `output/desk_tickets.html` (Cash tab), `output/resolved_tickets.json` and `output/resolved_board.html`.

## Safety rules

- **No real customers or vendors:** messages, restock requests and purchase orders are drafts on the board. Nothing is ever sent.
- **No real money:** "payments" are rows in a local SQLite file. Agents can only prepare payments. Cash moves only when a human approves, and agent names are rejected as approvers.
- **No negative balances:** cash only goes out, since revenue isn't modeled.
- **No invented data:** every fact comes from the database through the MCP server.
- **Token budget:** each run has a cap of 30 model requests and 200,000 tokens.
- **Secrets:** the API key comes only from the `PORTKEY_API_KEY` environment variable. No `.env` file is committed.

Full details are in `output/harness.md`.
