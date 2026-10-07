"""Data types shared by the Campus Customs agent team.

Each specialist returns a structured report (its PydanticAI output_type) so
the Boss receives typed facts -- copied from MCP tool output -- rather than
free text it would have to re-interpret.
"""

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["inventory", "accounting", "facilities", "customer_service"]


# --- Boss ------------------------------------------------------------------


class Delegation(BaseModel):
    """One task the Boss handed to a specialist, and what came back."""

    role: Role
    task: str = Field(description="What the Boss asked the specialist to do")
    summary: str = Field(description="One-line summary of the specialist's report")


class TicketPlan(BaseModel):
    """Boss output: the resolution plan for one ticket."""

    ticket_id: int
    ticket_type: str
    situation: str = Field(description="Facts about the ticket, taken from the database")
    delegations: list[Delegation] = Field(default_factory=list)
    recommended_actions: list[str] = Field(
        description="Next steps, in order, to resolve the ticket"
    )
    needs_human_approval: bool = Field(
        description="True if any action is a payment or a price override"
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="Rule-based reasons the ticket cannot be finished yet",
    )


# --- Specialists -----------------------------------------------------------


class InventoryReport(BaseModel):
    """Inventory output: stock position for the requested item."""

    sku: str
    size: str | None
    on_hand: int
    requested: int | None
    shortfall: int = Field(description="max(0, requested - on_hand)")
    other_sizes: dict[str, int] = Field(
        default_factory=dict, description="Stock by size for the same sku"
    )
    restock_vendor: str | None = None
    vendor_lead_days: int | None = None
    vendor_can_ship: bool | None = Field(
        default=None, description="False if the vendor has an open unpaid invoice"
    )
    notes: str = ""


class PurchaseOrder(BaseModel):
    """A restock order Accounting prepares. Needs human approval; never placed automatically."""

    vendor: str
    sku: str
    size: str | None
    qty: int
    unit_cost: float
    total_cost: float
    vendor_can_ship: bool | None = Field(default=None, description="False if the vendor has an open unpaid invoice")
    status: Literal["pending_approval", "approved"] = "pending_approval"


class AccountingReport(BaseModel):
    """Accounting output: what is owed, whether cash covers it, and any purchase order."""

    item: str = Field(description="What this is about, e.g. 'invoice 501', 'lease 1 rent', 'bulk discount'")
    amount_due: float | None = Field(default=None, description="Amount owed, if this is a bill")
    due_date: str | None = None
    days_overdue: int = 0
    cash_balance: float
    balance_after_payment: float | None = Field(default=None, description="Checking after the prepared payment(s)")
    can_pay: bool | None = Field(default=None, description="False if paying would make the balance negative")
    requires_human_approval: bool = True
    margin_check: str | None = Field(
        default=None, description="For price overrides: price vs. unit cost analysis"
    )
    purchase_order: PurchaseOrder | None = Field(
        default=None, description="Restock order prepared for human approval, if one is needed"
    )
    notes: str = ""


class FacilitiesReport(BaseModel):
    """Facilities output: lease / physical-space status."""

    lease_id: int
    space_name: str
    landlord: str
    monthly_rent: float
    next_due: str
    days_until_due: int
    notes: str = ""


class CustomerDraft(BaseModel):
    """Customer Service output: a reply draft. Drafts stay on the board -- never sent."""

    ticket_id: int
    to: str
    subject: str
    body: str
    status: Literal["draft"] = "draft"
