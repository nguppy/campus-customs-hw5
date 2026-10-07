"""Campus Customs MCP server.

Exposes the shop database (data/campus_customs_new.db) to the agent team as
MCP tools. Every tool must read from or write to the database -- tools never
invent data. If a record is not found, the tool says so instead of guessing.

Read tools report facts. Write tools enforce the shop rules themselves, so an
agent cannot break them even if it tries:
  - agents can only PREPARE payments and purchase orders (posted to the
    `board` as pending_approval); cash moves only in approve_board_item,
    which the backend calls when a human clicks Approve
  - payments need a named human approver and never overdraw an account
  - a vendor with an open invoice will not ship (restock requests and
    purchase-order approvals are refused)
  - customer/vendor messages are only posted to the `board` as drafts --
    nothing is ever sent
This server is the only code that touches the database.
"""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP

# Resolve the DB path from the project root so the server works no matter
# which directory it is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs")

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service",
               "customer service", "agent", "ai", "assistant"}
TICKET_STATUSES = {"open", "in_progress", "waiting_approval", "blocked", "resolved"}

BOARD_SCHEMA = """
CREATE TABLE IF NOT EXISTS board (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,          -- customer_draft | restock_request | purchase_order | payment_request | discount_request
    author TEXT NOT NULL,        -- agent role that posted it
    recipient TEXT,
    subject TEXT,
    body TEXT,
    details TEXT,                -- JSON with the facts behind the item
    status TEXT NOT NULL,        -- draft | pending_approval | approved
    created_at TEXT NOT NULL,    -- desk.date_today
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
)
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Open a connection to the working database; commit and close on exit.

    Raises FileNotFoundError rather than letting sqlite3 silently create an
    empty database (which would let tools "succeed" with no real data).
    If a tool raises midway, nothing is committed.
    Closing matters on Windows: an open handle would block resetting the DB.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["sku"]
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def rows_to_dicts(rows) -> list[dict]:
    """Convert sqlite3.Row results into plain dicts for JSON tool output."""
    return [dict(r) for r in rows]


def desk_today(conn: sqlite3.Connection) -> str:
    """The shop's "today" -- always desk.date_today, never the real clock."""
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    if row is None:
        raise ValueError("desk table has no date_today row")
    return row["date_today"]


def days_between(start: str, end: str) -> int:
    """Whole days from start to end (ISO dates). Negative if end is earlier."""
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def add_one_month(iso_day: str) -> str:
    """Same day next month, clamped to the month's last day (e.g. 01-31 -> 02-28)."""
    d = date.fromisoformat(iso_day[:10])
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    raise ValueError(f"cannot add a month to {iso_day}")


def refuse(reason: str, **facts) -> dict:
    """Uniform refusal: nothing was written to the database."""
    return {"ok": False, "refused": True, "reason": reason, "database_changed": False, **facts}


def ticket_exists(conn, ticket_id: int) -> bool:
    return conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is not None


def vendor_open_invoices(conn, vendor_id: int) -> list[dict]:
    return rows_to_dicts(conn.execute(
        "SELECT id, amount, due_date, description FROM invoices"
        " WHERE vendor_id = ? AND status = 'open' ORDER BY id", (vendor_id,)
    ).fetchall())


def ensure_board(conn: sqlite3.Connection) -> None:
    """The board holds drafts and pending items. A reset removes it; recreate on demand."""
    conn.execute(BOARD_SCHEMA)


def board_row(row) -> dict:
    item = dict(row)
    item["details"] = json.loads(item["details"]) if item["details"] else None
    return item


def post_to_board(conn, *, ticket_id, kind, author, recipient, subject, body, details, status) -> dict:
    ensure_board(conn)
    cur = conn.execute(
        "INSERT INTO board (ticket_id, kind, author, recipient, subject, body, details, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ticket_id, kind, author, recipient, subject, body,
         json.dumps(details) if details is not None else None, status, desk_today(conn)),
    )
    return board_row(conn.execute("SELECT * FROM board WHERE id = ?", (cur.lastrowid,)).fetchone())


def set_ticket_status(conn, ticket_id: int, status: str, note: str) -> dict:
    """Set a ticket's status and append "[desk date] old -> new: note" to its notes."""
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    line = f"[{desk_today(conn)}] {ticket['status']} -> {status}: {note}"
    notes = f"{ticket['notes']}\n{line}" if ticket["notes"] else line
    conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
    return dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())


def status_after_approval(conn, item: dict) -> tuple[str, str]:
    """Decide a ticket's status once a board item is approved.

    - other items for the ticket still pending      -> waiting_approval
    - rent paid on a rent_notice ticket             -> resolved
    - anything else (e.g. invoice paid, PO approved) -> in_progress: the
      approval unblocks the work, but the order itself is not fulfilled yet
    """
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (item["ticket_id"],)).fetchone()
    approved = f"Human approved board item {item['id']} ({item['subject']})"
    pending = conn.execute(
        "SELECT COUNT(*) FROM board WHERE ticket_id = ? AND status = 'pending_approval' AND id <> ?",
        (item["ticket_id"], item["id"]),
    ).fetchone()[0]
    if pending:
        return "waiting_approval", f"{approved}; {pending} item(s) still awaiting approval."
    d = item["details"]
    if item["kind"] == "payment_request" and d["kind"] == "rent" and ticket["type"] == "rent_notice":
        return "resolved", f"{approved}. Rent paid; nothing left to do."
    if item["kind"] == "payment_request" and d["kind"] == "invoice":
        return "in_progress", f"{approved}. Invoice paid; the vendor can ship again, so the order can proceed."
    if item["kind"] == "purchase_order":
        return "in_progress", f"{approved}. Purchase order paid; waiting for the vendor's delivery ({d.get('lead_days')} lead days)."
    if item["kind"] == "discount_request":
        return "in_progress", f"{approved}. Discounted price approved; the customer can be told."
    return "in_progress", f"{approved}."


def check_approver(approved_by: str) -> str | None:
    """Return a refusal reason if approved_by is not a plausible human name."""
    name = (approved_by or "").strip()
    if not name:
        return "Payment requires human approval: approved_by is empty."
    if name.lower() in AGENT_NAMES:
        return f"Payment requires human approval: '{name}' is an agent, not a human approver."
    return None


# --- Read tools ------------------------------------------------------------


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket that is not resolved (what is pending / needs action).

    Includes status open, in_progress, waiting_approval and blocked.
    Supports tickets 101, 102, 103.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status <> 'resolved' ORDER BY id"
        ).fetchall()
    return rows_to_dicts(rows)


@mcp.tool
def list_tickets() -> list[dict]:
    """List every ticket, open or resolved, with its current status.

    Supports tickets 101, 102, 103. (Backend /tickets route)
    """
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    return rows_to_dicts(rows)


@mcp.tool
def get_ticket_details(ticket_id: int) -> dict:
    """Return one ticket plus every record linked to it.

    Linked records: inventory + pricing (by sku/size), invoice + vendor (by
    invoice_id), lease (by lease_id), cash accounts, and desk.date_today.
    Due-date math is measured against desk.date_today. A vendor with any open
    invoice is reported as unable to ship new product.

    Supports tickets 101, 102, 103.
    """
    with get_conn() as conn:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if ticket is None:
            return {"error": f"Ticket {ticket_id} not found"}

        today = desk_today(conn)
        result = {"desk_date_today": today, "ticket": dict(ticket)}

        if ticket["sku"]:
            inv = conn.execute(
                "SELECT * FROM inventory WHERE sku = ? AND size = ?",
                (ticket["sku"], ticket["size"]),
            ).fetchone()
            result["inventory"] = dict(inv) if inv else None
            if inv and ticket["qty"] is not None:
                result["inventory"]["requested_qty"] = ticket["qty"]
                result["inventory"]["shortfall"] = max(0, ticket["qty"] - inv["qty"])

            price = conn.execute(
                "SELECT * FROM pricing WHERE sku = ?", (ticket["sku"],)
            ).fetchone()
            result["pricing"] = dict(price) if price else None

        if ticket["invoice_id"] is not None:
            invoice = conn.execute(
                "SELECT * FROM invoices WHERE id = ?", (ticket["invoice_id"],)
            ).fetchone()
            if invoice:
                result["invoice"] = dict(invoice)
                result["invoice"]["days_overdue"] = max(
                    0, days_between(invoice["due_date"], today)
                )
                vendor = conn.execute(
                    "SELECT * FROM vendors WHERE id = ?", (invoice["vendor_id"],)
                ).fetchone()
                open_count = conn.execute(
                    "SELECT COUNT(*) FROM invoices WHERE vendor_id = ? AND status = 'open'",
                    (invoice["vendor_id"],),
                ).fetchone()[0]
                result["vendor"] = dict(vendor) if vendor else None
                if vendor:
                    result["vendor"]["open_invoices"] = open_count
                    result["vendor"]["will_ship_new_product"] = open_count == 0
            else:
                result["invoice"] = None

        if ticket["lease_id"] is not None:
            lease = conn.execute(
                "SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)
            ).fetchone()
            if lease:
                result["lease"] = dict(lease)
                result["lease"]["days_until_due"] = days_between(today, lease["next_due"])
            else:
                result["lease"] = None

        result["cash_accounts"] = rows_to_dicts(
            conn.execute("SELECT * FROM cash_accounts ORDER BY name").fetchall()
        )
    return result


@mcp.tool
def check_inventory(sku: str, size: str | None = None) -> dict:
    """Return stock (qty, location) for a sku, for one size or all sizes.

    Supports tickets 101, 103.
    """
    with get_conn() as conn:
        if size is None:
            rows = conn.execute(
                "SELECT * FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)
            ).fetchall()
    if not rows:
        target = f"{sku} size {size}" if size else sku
        return {"error": f"No inventory found for {target}"}
    return {"sku": sku, "size": size, "items": rows_to_dicts(rows)}


@mcp.tool
def list_vendors() -> list[dict]:
    """List every vendor with specialty, lead_days, open invoices, and whether it will ship.

    A vendor with any open invoice will not ship new product.
    Supports tickets 101, 103 (restocking).
    """
    with get_conn() as conn:
        vendors = rows_to_dicts(conn.execute("SELECT * FROM vendors ORDER BY id").fetchall())
        for v in vendors:
            open_inv = vendor_open_invoices(conn, v["id"])
            v["open_invoices"] = open_inv
            v["open_invoice_total"] = sum(i["amount"] for i in open_inv)
            v["will_ship_new_product"] = not open_inv
    return vendors


@mcp.tool
def get_cash_position() -> dict:
    """Cash balances and every outstanding obligation (open invoices, upcoming rent).

    Shows the balance left if everything were paid. Revenue is not modeled, so
    cash only goes down. Supports tickets 101, 102, 103.
    """
    with get_conn() as conn:
        today = desk_today(conn)
        accounts = rows_to_dicts(conn.execute("SELECT * FROM cash_accounts ORDER BY name").fetchall())
        invoices = rows_to_dicts(conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id"
            " WHERE i.status = 'open' ORDER BY i.due_date"
        ).fetchall())
        for i in invoices:
            i["days_overdue"] = max(0, days_between(i["due_date"], today))
        leases = rows_to_dicts(conn.execute("SELECT * FROM leases ORDER BY next_due").fetchall())
        for lease in leases:
            lease["days_until_due"] = days_between(today, lease["next_due"])
    total_cash = sum(a["balance"] for a in accounts)
    obligations = sum(i["amount"] for i in invoices) + sum(lease["monthly_rent"] for lease in leases)
    return {
        "desk_date_today": today,
        "accounts": accounts,
        "open_invoices": invoices,
        "leases": leases,
        "total_cash": total_cash,
        "total_obligations": obligations,
        "cash_after_all_obligations": total_cash - obligations,
    }


@mcp.tool
def list_board(ticket_id: int | None = None) -> list[dict]:
    """List drafts and pending items on the board, optionally for one ticket.

    Supports tickets 101, 102, 103.
    """
    with get_conn() as conn:
        ensure_board(conn)
        if ticket_id is None:
            rows = conn.execute("SELECT * FROM board ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM board WHERE ticket_id = ? ORDER BY id", (ticket_id,)
            ).fetchall()
    return [board_row(r) for r in rows]


# --- Write tools -----------------------------------------------------------


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str) -> dict:
    """Set a ticket's status and append a dated note explaining why.

    status must be one of: open, in_progress, waiting_approval, blocked, resolved.
    Supports tickets 101, 102, 103. (Boss)
    """
    if status not in TICKET_STATUSES:
        return refuse(f"Invalid status '{status}'. Allowed: {sorted(TICKET_STATUSES)}")
    with get_conn() as conn:
        if not ticket_exists(conn, ticket_id):
            return refuse(f"Ticket {ticket_id} not found")
        updated = set_ticket_status(conn, ticket_id, status, note)
    return {"ok": True, "database_changed": True, "ticket": updated}


@mcp.tool
def save_draft(ticket_id: int, to: str, subject: str, body: str) -> dict:
    """Post a customer message draft to the board. Nothing is ever sent.

    Supports tickets 101, 102, 103. (Customer Service)
    """
    with get_conn() as conn:
        if not ticket_exists(conn, ticket_id):
            return refuse(f"Ticket {ticket_id} not found")
        item = post_to_board(
            conn, ticket_id=ticket_id, kind="customer_draft", author="customer_service",
            recipient=to, subject=subject, body=body, details=None, status="draft",
        )
    return {"ok": True, "database_changed": True, "sent": False, "board_item": item}


@mcp.tool
def request_restock(ticket_id: int, vendor_id: int, sku: str, size: str, qty: int) -> dict:
    """Post a restock request draft for a vendor to the board (never sent to the vendor).

    Refused if the vendor has an open unpaid invoice -- that vendor will not
    ship. Expected arrival = desk.date_today + vendors.lead_days.
    Supports tickets 101, 103. (Inventory)
    """
    if qty <= 0:
        return refuse("qty must be positive")
    with get_conn() as conn:
        if not ticket_exists(conn, ticket_id):
            return refuse(f"Ticket {ticket_id} not found")
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return refuse(f"Vendor {vendor_id} not found")
        item = conn.execute("SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if item is None:
            return refuse(f"No inventory item {sku} size {size}")
        blocking = vendor_open_invoices(conn, vendor_id)
        if blocking:
            return refuse(
                f"{vendor['name']} has an open unpaid invoice and will not ship new product.",
                vendor=dict(vendor), blocking_invoices=blocking,
            )
        eta = (date.fromisoformat(desk_today(conn)) + timedelta(days=vendor["lead_days"])).isoformat()
        details = {"vendor_id": vendor_id, "sku": sku, "size": size, "qty": qty,
                   "on_hand": item["qty"], "lead_days": vendor["lead_days"], "expected_arrival": eta}
        posted = post_to_board(
            conn, ticket_id=ticket_id, kind="restock_request", author="inventory",
            recipient=vendor["name"], subject=f"Restock {qty} x {sku} {size}",
            body=f"Request {qty} x {item['name']} ({sku}, size {size}). Expected arrival {eta}.",
            details=details, status="draft",
        )
    return {"ok": True, "database_changed": True, "sent": False, "board_item": posted}


@mcp.tool
def prepare_purchase_order(ticket_id: int, vendor_id: int, sku: str, size: str, qty: int) -> dict:
    """Prepare a purchase order for human approval and post it to the board.

    Cost = pricing.unit_cost x qty. Refused if the cost exceeds the checking
    balance (no negative balances). The PO is never placed and no cash moves.
    Supports tickets 101, 103. (Accounting)
    """
    if qty <= 0:
        return refuse("qty must be positive")
    with get_conn() as conn:
        if not ticket_exists(conn, ticket_id):
            return refuse(f"Ticket {ticket_id} not found")
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return refuse(f"Vendor {vendor_id} not found")
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return refuse(f"No inventory item {sku} size {size}")
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return refuse(f"No pricing for {sku}")
        cash = conn.execute("SELECT * FROM cash_accounts WHERE name = 'checking'").fetchone()
        total = round(price["unit_cost"] * qty, 2)
        if cash is None:
            return refuse("Cash account 'checking' not found")
        if total > cash["balance"]:
            return refuse(
                f"Purchase order total ${total:.2f} exceeds the checking balance.",
                total_cost=total, checking_balance=cash["balance"],
            )
        blocking = vendor_open_invoices(conn, vendor_id)
        details = {"vendor_id": vendor_id, "sku": sku, "size": size, "qty": qty,
                   "unit_cost": price["unit_cost"], "total_cost": total,
                   "checking_balance": cash["balance"], "balance_if_paid": cash["balance"] - total,
                   "vendor_can_ship": not blocking, "blocking_invoices": blocking,
                   "lead_days": vendor["lead_days"]}
        posted = post_to_board(
            conn, ticket_id=ticket_id, kind="purchase_order", author="accounting",
            recipient=vendor["name"], subject=f"PO: {qty} x {sku} {size} (${total:.2f})",
            body=f"Purchase {qty} x {sku} size {size} at ${price['unit_cost']:.2f} = ${total:.2f}.",
            details=details, status="pending_approval",
        )
    return {"ok": True, "database_changed": True, "placed": False, "board_item": posted}


def _record_payment(conn, *, kind: str, ref_id: int, amount: float, approved_by: str, account: str) -> dict:
    """Shared payment checks + bookkeeping. Returns a refusal, or the new payment row."""
    acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    if acct is None:
        return refuse(f"Cash account '{account}' not found")
    if amount > acct["balance"]:
        return refuse(
            f"Insufficient cash: paying ${amount:.2f} would overdraw '{account}'.",
            amount=amount, balance=acct["balance"], shortfall=round(amount - acct["balance"], 2),
        )
    today = desk_today(conn)
    cur = conn.execute(
        "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
        (kind, ref_id, amount, account, today, approved_by.strip()),
    )
    conn.execute(
        "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?", (amount, today, account)
    )
    payment = dict(conn.execute("SELECT * FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone())
    balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()[0]
    return {"ok": True, "payment": payment, "new_balance": balance}


@mcp.tool
def prepare_discount(ticket_id: int, unit_price: float, qty: int, reason: str) -> dict:
    """Propose a discounted unit price for a price-override ticket, for human approval.

    Uses the ticket's sku. Refused if unit_price is below pricing.unit_cost
    (the shop would lose money) or not below list_price (not a discount).
    Posts a discount_request (pending_approval) to the board with the margin
    math. No cash moves, now or on approval -- revenue is not modeled.
    Supports ticket 103. (Accounting)
    """
    if qty <= 0:
        return refuse("qty must be positive")
    with get_conn() as conn:
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return refuse(f"Ticket {ticket_id} not found")
        if not ticket["sku"]:
            return refuse(f"Ticket {ticket_id} has no sku to price")
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (ticket["sku"],)).fetchone()
        if price is None:
            return refuse(f"No pricing for {ticket['sku']}")
        if unit_price < price["unit_cost"]:
            return refuse(f"${unit_price:.2f} is below unit cost ${price['unit_cost']:.2f}; the shop would lose money.",
                          unit_cost=price["unit_cost"], list_price=price["list_price"])
        if unit_price >= price["list_price"]:
            return refuse(f"${unit_price:.2f} is not below list price ${price['list_price']:.2f}; no discount to approve.")
        ensure_board(conn)
        if conn.execute("SELECT 1 FROM board WHERE ticket_id = ? AND kind = 'discount_request' AND status = 'pending_approval'",
                        (ticket_id,)).fetchone():
            return refuse(f"A discount for ticket {ticket_id} is already pending approval")
        discount_pct = round(100 * (1 - unit_price / price["list_price"]), 1)
        details = {"sku": ticket["sku"], "qty": qty, "unit_price": unit_price,
                   "list_price": price["list_price"], "unit_cost": price["unit_cost"],
                   "discount_pct": discount_pct,
                   "total_price": round(unit_price * qty, 2),
                   "total_at_list": round(price["list_price"] * qty, 2),
                   "margin_per_unit": round(unit_price - price["unit_cost"], 2),
                   "total_margin": round((unit_price - price["unit_cost"]) * qty, 2),
                   "reason": reason, "cash_moves": False}
        posted = post_to_board(
            conn, ticket_id=ticket_id, kind="discount_request", author="accounting",
            recipient=ticket["requester"],
            subject=f"Discount: {qty} x {ticket['sku']} at ${unit_price:.2f} ({discount_pct}% off)",
            body=f"{qty} x {ticket['sku']} at ${unit_price:.2f} each instead of ${price['list_price']:.2f}. {reason}",
            details=details, status="pending_approval",
        )
    return {"ok": True, "database_changed": True, "cash_moved": False, "board_item": posted}


@mcp.tool
def prepare_payment(ticket_id: int, kind: str, ref_id: int) -> dict:
    """Prepare a payment for human approval and post it to the board. No cash moves.

    kind is "invoice" (ref_id = invoices.id) or "rent" (ref_id = leases.id).
    The amount always comes from the database. Refused if the invoice is not
    open, a request for the same bill is already pending, or checking cannot
    cover it. Cash moves only when a human approves it (approve_board_item).
    Supports tickets 101 (invoice), 102 (rent). (Accounting)
    """
    if kind not in ("invoice", "rent"):
        return refuse("kind must be 'invoice' or 'rent'")
    with get_conn() as conn:
        if not ticket_exists(conn, ticket_id):
            return refuse(f"Ticket {ticket_id} not found")
        today = desk_today(conn)
        if kind == "invoice":
            inv = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id"
                " WHERE i.id = ?", (ref_id,)
            ).fetchone()
            if inv is None:
                return refuse(f"Invoice {ref_id} not found")
            if inv["status"] != "open":
                return refuse(f"Invoice {ref_id} is '{inv['status']}', not open")
            amount, payee, due = inv["amount"], inv["vendor_name"], inv["due_date"]
            label = f"invoice {ref_id}"
        else:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return refuse(f"Lease {ref_id} not found")
            amount, payee, due = lease["monthly_rent"], lease["landlord"], lease["next_due"]
            label = f"rent for lease {ref_id} ({lease['space_name']})"
        ensure_board(conn)
        for row in conn.execute(
            "SELECT id, details FROM board WHERE kind = 'payment_request' AND status = 'pending_approval'"
        ).fetchall():
            d = json.loads(row["details"])
            if d["kind"] == kind and d["ref_id"] == ref_id:
                return refuse(f"A payment request for {label} is already pending (board item {row['id']})")
        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()
        if cash is None:
            return refuse("Cash account 'checking' not found")
        if amount > cash["balance"]:
            return refuse(f"Insufficient cash: ${amount:.2f} exceeds checking (${cash['balance']:.2f}).",
                          amount=amount, balance=cash["balance"])
        details = {"kind": kind, "ref_id": ref_id, "amount": amount, "payee": payee, "due": due,
                   "days_until_due": days_between(today, due),
                   "checking_balance": cash["balance"], "balance_if_paid": cash["balance"] - amount}
        posted = post_to_board(
            conn, ticket_id=ticket_id, kind="payment_request", author="accounting",
            recipient=payee, subject=f"Pay {label}: ${amount:.2f}",
            body=f"Pay ${amount:.2f} to {payee} for {label}, due {due}.",
            details=details, status="pending_approval",
        )
    return {"ok": True, "database_changed": True, "cash_moved": False, "board_item": posted}


@mcp.tool
def approve_board_item(board_id: int, approved_by: str) -> dict:
    """Execute a pending payment or purchase order after a HUMAN approves it.

    Called by the backend /approvals route when a person clicks Approve --
    agents are not given this tool. approved_by must be a human name.
      - payment_request (invoice): pays it, marks the invoice paid
      - payment_request (rent): pays it, moves the lease's next_due forward a month
      - purchase_order: pays unit_cost x qty; refused while the vendor has an open invoice
      - discount_request: approves the discounted price; no cash moves
        (revenue is not modeled)
    Every payment / purchase-order approval adds a payments row and lowers
    checking; refused if cash is short (no negative balances). Drafts (messages, restock requests) cannot
    be approved -- they are never sent.
    The ticket's status is then updated: waiting_approval if other items are
    still pending, resolved once rent is paid on a rent notice, otherwise
    in_progress (the approval unblocks the work). Resolved tickets stay resolved.
    """
    if reason := check_approver(approved_by):
        return refuse(reason)
    with get_conn() as conn:
        ensure_board(conn)
        row = conn.execute("SELECT * FROM board WHERE id = ?", (board_id,)).fetchone()
        if row is None:
            return refuse(f"Board item {board_id} not found")
        item = board_row(row)
        if item["status"] != "pending_approval":
            return refuse(f"Board item {board_id} is '{item['status']}', not pending approval")
        d = item["details"]

        if item["kind"] == "payment_request" and d["kind"] == "invoice":
            inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (d["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return refuse(f"Invoice {d['ref_id']} is no longer open")
            result = _record_payment(conn, kind="invoice", ref_id=inv["id"], amount=inv["amount"],
                                     approved_by=approved_by, account="checking")
            if not result["ok"]:
                return result
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (inv["id"],))
            result["invoice"] = dict(conn.execute("SELECT * FROM invoices WHERE id = ?", (inv["id"],)).fetchone())

        elif item["kind"] == "payment_request" and d["kind"] == "rent":
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (d["ref_id"],)).fetchone()
            if lease is None:
                return refuse(f"Lease {d['ref_id']} not found")
            result = _record_payment(conn, kind="rent", ref_id=lease["id"], amount=lease["monthly_rent"],
                                     approved_by=approved_by, account="checking")
            if not result["ok"]:
                return result
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?",
                         (add_one_month(lease["next_due"]), lease["id"]))
            result["lease"] = dict(conn.execute("SELECT * FROM leases WHERE id = ?", (lease["id"],)).fetchone())

        elif item["kind"] == "purchase_order":
            vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (d["vendor_id"],)).fetchone()
            blocking = vendor_open_invoices(conn, d["vendor_id"])
            if blocking:
                return refuse(f"{vendor['name']} has an open unpaid invoice and will not ship; pay it first.",
                              blocking_invoices=blocking)
            price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (d["sku"],)).fetchone()
            total = round(price["unit_cost"] * d["qty"], 2)
            result = _record_payment(conn, kind="purchase_order", ref_id=board_id, amount=total,
                                     approved_by=approved_by, account="checking")
            if not result["ok"]:
                return result

        elif item["kind"] == "discount_request":
            # A price decision, not a payment: revenue is not modeled, so no cash moves.
            result = {"ok": True, "payment": None, "cash_moved": False}

        else:
            return refuse(f"Board item {board_id} is a {item['kind']}; only payments, purchase orders and discounts are approved")

        d.update(approved_by=approved_by.strip(), payment_id=result["payment"]["id"] if result["payment"] else None)
        conn.execute("UPDATE board SET status = 'approved', details = ? WHERE id = ?", (json.dumps(d), board_id))
        result["board_item"] = board_row(conn.execute("SELECT * FROM board WHERE id = ?", (board_id,)).fetchone())

        # Keep the ticket in step with the approval (never reopen a resolved ticket).
        ticket = conn.execute("SELECT status FROM tickets WHERE id = ?", (item["ticket_id"],)).fetchone()
        if ticket is not None and ticket["status"] != "resolved":
            status, note = status_after_approval(conn, result["board_item"])
            result["ticket"] = set_ticket_status(conn, item["ticket_id"], status, note)
    return {**result, "database_changed": True}


if __name__ == "__main__":
    mcp.run(show_banner=False)
