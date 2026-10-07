"""Boss agent -- reads each ticket, decides who should work on it, and makes final calls.

The Boss reads tickets through the MCP server, hands specialist work to
Inventory, Accounting, Facilities and Customer Service through delegation
tools, records the outcome with update_ticket_status, and combines the
specialists' typed reports into a TicketPlan.
"""

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import RunUsage

from backend.accounting import run_accounting
from backend.audit import audited_run
from backend.customer_service import run_customer_service
from backend.facilities import run_facilities
from backend.inventory import run_inventory
from backend.llm import TEAM_LIMITS, build_model, campus_tools, load_prompt
from backend.models import TicketPlan

boss_agent = Agent(
    build_model(),
    name="boss",
    retries=3,  # let the model fix a malformed report instead of failing the run
    instructions=lambda: load_prompt("boss"),  # re-read each run, so edits apply and the audit hash matches
    output_type=TicketPlan,
    toolsets=[campus_tools(
        "list_open_tickets",
        "get_ticket_details",
        "list_board",
        "update_ticket_status",
    )],
)


# --- Delegation tools ------------------------------------------------------
# Each passes ctx.usage so the specialists' token use counts toward the same
# per-ticket budget, and returns the specialist's typed report as JSON.


@boss_agent.tool
async def ask_inventory(ctx: RunContext, task: str) -> str:
    """Delegate to Inventory: stock by SKU/size, shortfalls, which vendor can restock, restock requests. Include the ticket id."""
    return (await run_inventory(task, usage=ctx.usage)).model_dump_json()


@boss_agent.tool
async def ask_accounting(ctx: RunContext, task: str) -> str:
    """Delegate to Accounting: cash, invoices, margins, payments and purchase orders (human approval). Include the ticket id."""
    return (await run_accounting(task, usage=ctx.usage)).model_dump_json()


@boss_agent.tool
async def ask_facilities(ctx: RunContext, task: str) -> str:
    """Delegate to Facilities: the shop-space side (leases, rent, etc.). Include the ticket id."""
    return (await run_facilities(task, usage=ctx.usage)).model_dump_json()


@boss_agent.tool
async def ask_customer_service(ctx: RunContext, task: str) -> str:
    """Delegate to Customer Service: draft a message for the customer (posted to the board, never sent). Include the ticket id and the facts to reflect."""
    return (await run_customer_service(task, usage=ctx.usage)).model_dump_json()


async def run_boss(ticket_id: int, usage: RunUsage | None = None) -> TicketPlan:
    """Run the Boss agent loop on one ticket and return its plan."""
    result = await audited_run(
        boss_agent, "boss",
        f"Work ticket {ticket_id}. Delegate to the right specialists, record the ticket status, and return a TicketPlan.",
        usage=usage, usage_limits=TEAM_LIMITS,
    )
    return result.output
