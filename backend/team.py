"""Run the agent team on tickets -- used by the FastAPI routes and the CLI.

Every run is appended to output/audit_trail.json (earlier runs are kept).

CLI (from the project root) -- resets the DB, then works the open tickets:
    python -m backend.team            # all open tickets
    python -m backend.team 101 103    # specific tickets
"""

import asyncio
import shutil
import sys

from fastmcp import Client
from pydantic_ai.usage import RunUsage

from backend import audit
from backend.boss import run_boss
from backend.llm import PROJECT_ROOT, mcp_config
from backend.models import TicketPlan

ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"


def reset_db() -> None:
    """Rule 7: restore the working copy to the original values before a fresh run."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)


async def open_ticket_ids() -> list[int]:
    """Read the open queue through the MCP server, like every other fact."""
    async with Client(mcp_config()) as client:
        result = await client.call_tool("list_open_tickets", {})
    return [t["id"] for t in result.structured_content["result"]]


def _usage_dict(usage: RunUsage) -> dict:
    return {"requests": usage.requests, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}


async def run_ticket(ticket_id: int, *, run_id: str | None = None, db_reset: bool = False) -> TicketPlan:
    """One audited run: the Boss (and the specialists it delegates to) works one ticket."""
    audit.start_run([ticket_id], db_reset=db_reset, run_id=run_id)
    usage = RunUsage()  # one budget per ticket, shared by Boss + specialists
    try:
        plan = await run_boss(ticket_id, usage=usage)
        audit.record_ticket_result(ticket_id, plan, _usage_dict(usage))
    except BaseException as exc:
        audit.finish_run("error", total_usage=_usage_dict(usage), error=f"{type(exc).__name__}: {exc}")
        raise
    audit.finish_run("completed", total_usage=_usage_dict(usage))
    return plan


async def main(ticket_ids: list[int]) -> None:
    reset_db()
    for i, tid in enumerate(ticket_ids or await open_ticket_ids()):
        print(f"\n=== Ticket {tid} ===")
        plan = await run_ticket(tid, db_reset=(i == 0))
        print(plan.model_dump_json(indent=2))
    print(f"\nAudit trail appended to {audit.AUDIT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    asyncio.run(main([int(a) for a in sys.argv[1:]]))
