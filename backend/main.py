"""Campus Customs backend -- FastAPI routes for the desk dashboard.

Start it from backend/:
    uvicorn main:app --reload --port 8000
then open http://localhost:8000/docs to try the routes.

Every fact these routes return comes from the campus-customs MCP server
(the same .mcp.json connection the agents use) -- the backend never reads the
database directly. The one exception is /reset, which copies the original
database file over the working copy.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# `uvicorn main:app` runs from backend/, so put the project root on the path
# for the `backend.*` and `mcp_server` imports.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastmcp import Client  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend import audit, team  # noqa: E402
from backend.llm import mcp_config  # noqa: E402

# One team run at a time: runs, approvals and resets all change the same DB.
run_lock = asyncio.Lock()
state: dict = {"current": None, "last": None, "last_reset_at": None}


app = FastAPI(title="Campus Customs backend")

# Only the Vite dashboard page may call these routes from a browser.
DASHBOARD_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=DASHBOARD_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def mcp(tool: str, args: dict | None = None):
    """Call a campus-customs MCP tool and return its data.

    Opens a fresh MCP connection per call: nothing long-lived blocks
    uvicorn's --reload, and edits to mcp_server/server.py apply immediately.
    """
    async with Client(mcp_config()) as client:
        result = await client.call_tool(tool, args or {})
    data = result.structured_content
    return data.get("result", data) if isinstance(data, dict) else data


async def checking_balance() -> dict:
    cash = await mcp("get_cash_position")
    acct = next((a for a in cash["accounts"] if a["name"] == "checking"), None)
    if acct is None:
        raise HTTPException(404, "No 'checking' account in cash_accounts")
    return {"account": "checking", "balance": acct["balance"], "as_of": acct["date"]}


# --- Routes ----------------------------------------------------------------


@app.get("/")
async def index():
    """List the routes (handy when checking the server is up)."""
    return {
        "service": "Campus Customs backend",
        "routes": {
            "GET /tickets": "the tickets and whether each is open or resolved",
            "POST /tickets/{ticket_id}/run": "run the agent team on one ticket (in the background)",
            "GET /events": "recent agent events: what each agent said and which tools it used",
            "GET /approvals": "payments and purchase orders waiting for a human",
            "POST /approvals/{board_id}/approve": "human approves -> cash actually moves",
            "GET /cash": "current checking balance",
            "POST /reset": "restore the database to the original values",
        },
        "docs": "/docs",
    }


@app.get("/tickets")
async def get_tickets():
    """Every ticket with its status, and whether it is open or resolved."""
    tickets = await mcp("list_tickets")
    return [
        {"id": t["id"], "type": t["type"], "requester": t["requester"], "subject": t["subject"],
         "status": t["status"], "state": "resolved" if t["status"] == "resolved" else "open",
         "sku": t["sku"], "size": t["size"], "qty": t["qty"], "notes": t["notes"], "created_at": t["created_at"]}
        for t in tickets
    ]


async def _run_in_background(ticket_id: int, run_id: str) -> None:
    async with run_lock:
        state["current"] = {"run_id": run_id, "ticket_id": ticket_id, "started_at": _now()}
        try:
            plan = await team.run_ticket(ticket_id, run_id=run_id)
            state["last"] = {**state["current"], "finished_at": _now(), "status": "completed",
                             "plan": plan.model_dump()}
        except Exception as exc:  # recorded in the audit trail by team.run_ticket
            state["last"] = {**state["current"], "finished_at": _now(), "status": "error",
                             "error": f"{type(exc).__name__}: {exc}"}
        finally:
            state["current"] = None


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int):
    """Start the agent team on one ticket. Poll /events to watch it work."""
    if run_lock.locked():
        raise HTTPException(409, f"A run is already in progress: {state['current']}")
    details = await mcp("get_ticket_details", {"ticket_id": ticket_id})
    if "error" in details:
        raise HTTPException(404, details["error"])
    run_id = str(uuid.uuid4())
    asyncio.create_task(_run_in_background(ticket_id, run_id))
    return {"run_id": run_id, "ticket_id": ticket_id, "status": "started",
            "watch": f"/events?ticket_id={ticket_id}"}


@app.get("/events")
async def get_events(limit: int = Query(50, ge=1, le=500), ticket_id: int | None = None):
    """Recent agent events (oldest first), plus whether a run is in progress.

    Event types: tool_call (agent used a tool), tool_result (what the tool
    returned), said (agent text), report (agent's final typed report), error.
    """
    return {
        "running": state["current"],
        "last_run": state["last"],
        "events": audit.recent_events(limit=limit, ticket_id=ticket_id),
    }


@app.get("/approvals")
async def get_approvals(ticket_id: int | None = None):
    """Payments and purchase orders the agents prepared, waiting for a human."""
    board = await mcp("list_board", {"ticket_id": ticket_id} if ticket_id is not None else {})
    return [item for item in board if item["status"] == "pending_approval"]


class Approval(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human who clicked Approve")


@app.post("/approvals/{board_id}/approve")
async def approve(board_id: int, body: Approval):
    """A human clicked Approve: execute the payment or purchase order. This is what moves cash."""
    if run_lock.locked():
        raise HTTPException(409, "Wait for the current agent run to finish before approving.")
    result = await mcp("approve_board_item", {"board_id": board_id, "approved_by": body.approved_by})
    if not result.get("ok"):
        raise HTTPException(409, result.get("reason", "Approval refused"))
    audit.log_human_action("approve", board_id=board_id, approved_by=body.approved_by, result=result)
    return result


@app.get("/cash")
async def get_cash():
    """Current checking balance from cash_accounts."""
    return await checking_balance()


@app.post("/reset")
async def reset():
    """Restore data/campus_customs_new.db to the original values for a fresh run."""
    if run_lock.locked():
        raise HTTPException(409, "Cannot reset while an agent run is in progress.")
    team.reset_db()
    state["last_reset_at"] = _now()
    audit.log_human_action("reset")
    return {"reset": True, "at": state["last_reset_at"], "cash": await checking_balance(),
            "tickets": await get_tickets()}
