"""Accounting agent -- watches cash and invoices, checks margins, and prepares
payments or purchase orders for human approval.

Specialist on the Campus Customs team. The Boss delegates tasks here via
run_accounting(). Accounting can only PREPARE payments and purchase orders
(posted to the board as pending_approval); it has no tool that moves cash.
Cash moves only when a human clicks Approve on the dashboard, which calls the
backend's /approvals route. Every step goes to the audit trail.
"""

from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage

from backend.audit import audited_run
from backend.llm import TEAM_LIMITS, build_model, campus_tools, load_prompt
from backend.models import AccountingReport

accounting_agent = Agent(
    build_model(),
    name="accounting",
    retries=3,  # let the model fix a malformed report instead of failing the run
    instructions=lambda: load_prompt("accounting"),  # re-read each run, so edits apply and the audit hash matches
    output_type=AccountingReport,
    toolsets=[campus_tools(
        "get_ticket_details",
        "get_cash_position",
        "list_vendors",
        "prepare_purchase_order",
        "prepare_payment",
        "prepare_discount",
    )],
)


async def run_accounting(task: str, usage: RunUsage | None = None) -> AccountingReport:
    """Run the Accounting agent loop on one task and return its typed report."""
    result = await audited_run(accounting_agent, "accounting", task, usage=usage, usage_limits=TEAM_LIMITS)
    return result.output
