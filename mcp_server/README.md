# campus-customs MCP server

FastMCP server that gives the Campus Customs agent team access to the shop
database `data/campus_customs_new.db`. It is the **only** code that reads or
writes the database: agents get every fact and take every action through these
tools. There is no other shop-tools layer.

- **Entry point:** `mcp_server/server.py`
- **Server name:** `campus-customs`
- **Transport:** stdio
- **Registered in:** `.mcp.json` at the project root
- **Python:** the project's `.venv`

## Run / connect

The agents (`backend/llm.py`) and Claude Code both launch the server from `.mcp.json`.
To start it by hand:

```bash
.venv/Scripts/python.exe mcp_server/server.py
```

## Rules the server enforces

- **No invented data.** Every value comes from the database. A missing record returns `error` / `refused` with a reason, never a guess.
- **"Today" is `desk.date_today`.** All due and overdue math uses it, not the real clock.
- **Only humans move cash.** Agents can only *prepare* payments (`prepare_payment`) and purchase orders (`prepare_purchase_order`). Cash moves only in `approve_board_item`, which no agent is given; the backend calls it when a human clicks Approve (`POST /approvals/{board_id}/approve`). It refuses unless `approved_by` is a human name: empty values and agent names such as "accounting" or "boss" are refused.
- **No negative balances.** A payment or purchase order larger than the account balance is refused, both when it's prepared and when it's approved.
- **No shipping on unpaid invoices.** `request_restock` refuses a vendor with an open invoice, and so does approving a purchase order from that vendor.
- **Drafts only.** Customer messages and restock requests are posted to the `board` table as `draft`. Payments and purchase orders are posted as `pending_approval`. Nothing is ever sent, and drafts can't be approved.
- **All or nothing.** A refusal changes nothing (`database_changed: false`). A successful write commits as one transaction.

## Tools

| Tool | Access | Tables | Used by | Tickets |
|---|---|---|---|---|
| `list_open_tickets()` | read | tickets | Boss | 101, 102, 103 |
| `list_tickets()` | read | tickets | backend `/tickets` | 101, 102, 103 |
| `get_ticket_details(ticket_id)` | read | tickets, inventory, pricing, invoices, vendors, leases, cash_accounts, desk | all agents | 101, 102, 103 |
| `check_inventory(sku, size=None)` | read | inventory | Inventory, Customer Service | 101, 103 |
| `list_vendors()` | read | vendors, invoices | Inventory, Accounting | 101, 103 |
| `get_cash_position()` | read | cash_accounts, invoices, vendors, leases, desk | Accounting, Facilities | 101, 102, 103 |
| `list_board(ticket_id=None)` | read | board | Boss | 101, 102, 103 |
| `update_ticket_status(ticket_id, status, note)` | write | tickets, desk | Boss | 101, 102, 103 |
| `save_draft(ticket_id, to, subject, body)` | write (draft) | board, tickets, desk | Customer Service | 101, 102, 103 |
| `request_restock(ticket_id, vendor_id, sku, size, qty)` | write (draft) | board, vendors, invoices, inventory, tickets, desk | Inventory | 101, 103 |
| `prepare_purchase_order(ticket_id, vendor_id, sku, size, qty)` | write (pending approval) | board, pricing, cash_accounts, vendors, invoices, inventory, tickets, desk | Accounting | 101, 103 |
| `prepare_payment(ticket_id, kind, ref_id)` | write (pending approval) | board, invoices, vendors, leases, cash_accounts, tickets, desk | Accounting | 101, 102 |
| `prepare_discount(ticket_id, unit_price, qty, reason)` | write (pending approval, no cash) | board, tickets, pricing, desk | Accounting | 103 |
| `approve_board_item(board_id, approved_by)` | write (**moves cash**, human only) | board, payments, cash_accounts, invoices, leases, pricing, vendors, desk | backend approve route (no agent) | 101, 102, 103 |

### Read tools
- **`list_open_tickets`**: every ticket whose status isn't `resolved`.
- **`list_tickets`**: every ticket, open or resolved.
- **`get_ticket_details`**: one ticket plus its linked inventory and shortfall, pricing, invoice (with `days_overdue`), vendor (with `will_ship_new_product`), lease (with `days_until_due`), cash accounts and `desk_date_today`.
- **`check_inventory`**: qty and location for one size, or all sizes of a sku.
- **`list_vendors`**: each vendor's specialty, `lead_days`, open invoices, `open_invoice_total` and `will_ship_new_product`.
- **`get_cash_position`**: accounts, open invoices, leases, `total_cash`, `total_obligations` and `cash_after_all_obligations`.
- **`list_board`**: drafts and pending items, for all tickets or one.

### Write tools
- **`update_ticket_status`**:
  - Allowed statuses: `open`, `in_progress`, `waiting_approval`, `blocked`, `resolved`.
  - Appends `[desk date] old -> new: note` to `tickets.notes`.
- **`save_draft`**: posts a `customer_draft` with status `draft` to the board.
- **`request_restock`**:
  - Posts a `restock_request` draft with `expected_arrival` = desk date + `lead_days`.
  - Refused if the vendor has an open invoice.
- **`prepare_purchase_order`**:
  - Posts a `purchase_order` with status `pending_approval`, costed at `unit_cost` × qty.
  - Refused if the cost is more than the checking balance. Never placed.
- **`prepare_payment`**:
  - Posts a `payment_request` (`pending_approval`) for an invoice (`kind="invoice"`) or rent (`kind="rent"`), with the amount taken from the database. No cash moves.
  - Refused if the bill isn't open, a request for it is already pending, or checking can't cover it.
- **`prepare_discount`**:
  - Posts a `discount_request` (`pending_approval`) for the ticket's sku, with the discount %, total price and margin.
  - Refused below `unit_cost`, at or above `list_price`, or if a discount is already pending. No cash moves.
- **`approve_board_item`**: called by the backend when a human approves. A discount approval moves no cash and adds no `payments` row. Every approval adds a `payments` row with the human's name, lowers checking, and marks the board item `approved`.
  - **Invoice:** paid, and the invoice is set to `paid`.
  - **Rent:** paid, and `leases.next_due` moves forward a month.
  - **Purchase order:** pays `unit_cost` × qty. Refused while the vendor has an open invoice.
  - Also refused for a non-human approver, an item that isn't pending, or a shortfall in cash.
  - Then updates the ticket's status:
    - `waiting_approval` if other items for the ticket are still pending
    - `resolved` once rent is paid on a rent notice
    - `in_progress` otherwise
    - A resolved ticket stays resolved, and every change appends a dated note.

## The `board` table

This table isn't in the original database. The server creates it the first time something is posted, so resetting the database clears it.

Columns:
- `id`, `ticket_id`
- `kind`: `customer_draft`, `restock_request`, `purchase_order`, `payment_request` or `discount_request`
- `author`, `recipient`, `subject`, `body`
- `details`: JSON with the facts behind the item
- `status`: `draft`, `pending_approval` or `approved`
- `created_at`: the desk date

## Tests

- **`output/mcp_smoke.json`** (Problem 4): the three original read tools, checked against the database.
- **Problem 5:** every tool, including each refusal case, was run over MCP against a freshly reset database, which was reset again afterward.
- **Problem 7:** `prepare_payment` and `approve_board_item` were tested over MCP and through the backend routes. The tests covered agent-name refusal, duplicate requests, a purchase order blocked by an unpaid invoice, approving a draft, and checking the cash after each approval.
