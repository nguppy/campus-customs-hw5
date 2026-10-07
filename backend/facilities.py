"""Facilities agent -- handles the shop-space side (leases, rent, etc.).

Specialist on the Campus Customs team. The Boss delegates tasks here via
run_facilities(). The agent loop (model -> MCP tool calls -> model ... -> typed
FacilitiesReport) is run by PydanticAI, and every step is written to the audit trail.
"""

from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage

from backend.audit import audited_run
from backend.llm import TEAM_LIMITS, build_model, campus_tools, load_prompt
from backend.models import FacilitiesReport

facilities_agent = Agent(
    build_model(),
    name="facilities",
    retries=3,  # let the model fix a malformed report instead of failing the run
    instructions=lambda: load_prompt("facilities"),  # re-read each run, so edits apply and the audit hash matches
    output_type=FacilitiesReport,
    toolsets=[campus_tools(
        "get_ticket_details",
        "get_cash_position",
    )],
)


async def run_facilities(task: str, usage: RunUsage | None = None) -> FacilitiesReport:
    """Run the Facilities agent loop on one task and return its typed report."""
    result = await audited_run(facilities_agent, "facilities", task, usage=usage, usage_limits=TEAM_LIMITS)
    return result.output
