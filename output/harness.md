# Campus Customs — Agent Harness

Working database: `data/campus_customs_new.db` (copy of `data/campus_customs.db`)

**Contents:** Operating rules · Data tables · Agents · MCP tools · Backend routes · Dashboard · Audit trail · Safety · Problem 9 results

| How to run | Command (from the folder shown) |
|---|---|
| Backend API (`backend/`) | `uvicorn main:app --reload --port 8000`, which serves http://localhost:8000 |
| Dashboard (`frontend/`) | `npm run dev`, which opens http://localhost:5173 |
| Team from the command line (project root) | `python -m backend.team [ticket ids]` |

## Operating rules

1. **"Today" comes from `desk.date_today`.** All overdue checks are measured against this date as stored (currently `2026-08-31`), not against the real calendar date.
2. **Vendor lead times come from `vendors.lead_days`.** Do not assume or invent lead times.
3. **No shipments while an invoice is unpaid.** A vendor will not ship new product while it has an `open` invoice in `invoices`.
4. **Payments need human approval.** Agents only *prepare* payments and purchase orders. Cash moves only when a human clicks Approve on the dashboard (`POST /approvals/{board_id}/approve`), with their name as the approver. When a payment is approved and made:
   - add a row to `payments` (with `approved_by`)
   - lower the balance in `cash_accounts`
   - update the related record (for example, set the invoice `status` to paid, or move the lease's `next_due` forward)
5. **No negative balances.** If the account doesn't have enough cash, the pay tool must refuse the payment.
6. **Cash only goes out.** Revenue is not modeled, so no money comes in and balances never go up.
7. **Reset before resolving tickets.** Before working the tickets, restore `data/campus_customs_new.db` to the original values from `data/campus_customs.db`.
8. **Drafts only, no outside contact.** Never email customers or contact real vendors. Customer replies and vendor messages are written as drafts that stay on the board.
9. **Model:** all agents use `gpt-6-luna` only, called through the Portkey AI gateway. The API key is read from the `PORTKEY_API_KEY` environment variable and is never written into code or files.

## Data tables

### desk
| Field | Type |
|---|---|
| date_today | TEXT |
| notes | TEXT |

**Why it matters:** Sets the shop's "today" (2026-08-31), which is the date we use to judge what is due or overdue.

### tickets
| Field | Type |
|---|---|
| id | INTEGER (PK) |
| type | TEXT |
| requester | TEXT |
| subject | TEXT |
| sku | TEXT |
| size | TEXT |
| qty | INTEGER |
| lease_id | INTEGER (FK → leases.id) |
| invoice_id | INTEGER (FK → invoices.id) |
| status | TEXT |
| notes | TEXT |
| created_at | TEXT |

**Why it matters:** Holds the open requests (customer orders, rent, discounts) that the agent team has to handle.

### inventory
| Field | Type |
|---|---|
| sku | TEXT (PK) |
| name | TEXT |
| size | TEXT (PK) |
| qty | INTEGER |
| location | TEXT |

**Why it matters:** Important because it tells us stock availability.

### pricing
| Field | Type |
|---|---|
| sku | TEXT (PK) |
| unit_cost | REAL |
| list_price | REAL |

**Why it matters:** Important because it tells us how much items will cost.

### invoices
| Field | Type |
|---|---|
| id | INTEGER (PK) |
| vendor_id | INTEGER (FK → vendors.id) |
| amount | REAL |
| due_date | TEXT |
| status | TEXT |
| description | TEXT |

**Why it matters:** Important because it tells us what we owe vendors and when it is due. An `open` status means the bill is still unpaid; completed payments are recorded in `payments`.

### vendors
| Field | Type |
|---|---|
| id | INTEGER (PK) |
| name | TEXT |
| specialty | TEXT |
| lead_days | INTEGER |

**Why it matters:** Tells us who is providing our inventory.

### payments
| Field | Type |
|---|---|
| id | INTEGER (PK) |
| kind | TEXT |
| ref_id | INTEGER |
| amount | REAL |
| account | TEXT |
| paid_at | TEXT |
| approved_by | TEXT |

**Why it matters:** Supports our understanding of cash flow.

### cash_accounts
| Field | Type |
|---|---|
| name | TEXT (PK) |
| balance | REAL |
| date | TEXT |

**Why it matters:** Supports our understanding of cash flow.

### leases
| Field | Type |
|---|---|
| id | INTEGER (PK) |
| space_name | TEXT |
| landlord | TEXT |
| monthly_rent | REAL |
| next_due | TEXT |
| notes | TEXT |

**Why it matters:** Tells us our existing physical locations and cash flow.

### board (created by the MCP server)
| Field | Type |
|---|---|
| id | INTEGER (PK) |
| ticket_id | INTEGER (FK → tickets.id) |
| kind | TEXT (`customer_draft`, `restock_request`, `purchase_order`, `payment_request`, `discount_request`) |
| author | TEXT (agent role) |
| recipient | TEXT |
| subject | TEXT |
| body | TEXT |
| details | TEXT (JSON facts behind the item) |
| status | TEXT (`draft`, `pending_approval`, `approved`) |
| created_at | TEXT (`desk.date_today`) |

**Why it matters:** This is "the board," where drafts and pending items stay. Nothing on it is ever sent to a real customer or vendor. It isn't in the original database: the MCP server creates it the first time a draft is posted, so a database reset clears it.

## Agents

All five agents are PydanticAI agents on `gpt-6-luna` (via Portkey, `PORTKEY_API_KEY`). Each has one prompt file in `backend/prompts/` and one agent file in `backend/`. Every fact they use and every action they take goes through the `campus-customs` MCP server; no agent touches the database directly.

| Agent | Role | File | MCP tools it can call | Output |
|---|---|---|---|---|
| **Boss** | Reads each ticket, decides who should work on it, and makes final calls. | `backend/boss.py` | `list_open_tickets`, `get_ticket_details`, `list_board`, `update_ticket_status`, plus delegation to the 4 specialists | `TicketPlan` |
| **Inventory** | Checks stock by SKU and size, spots shortfalls, and figures out which vendor can restock. | `backend/inventory.py` | `get_ticket_details`, `check_inventory`, `list_vendors`, `request_restock` | `InventoryReport` |
| **Accounting** | Watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval. | `backend/accounting.py` | `get_ticket_details`, `get_cash_position`, `list_vendors`, `prepare_purchase_order`, `prepare_payment`, `prepare_discount` | `AccountingReport` |
| **Facilities** | Handles the shop-space side (leases, rent, etc.). | `backend/facilities.py` | `get_ticket_details`, `get_cash_position` | `FacilitiesReport` |
| **Customer Service** | Drafts messages for customers. | `backend/customer_service.py` | `get_ticket_details`, `check_inventory`, `save_draft` | `CustomerDraft` |

**How the agents run:**
- **Prompts:** each agent's prompt is re-read from `backend/prompts/<role>.md` on every run, so prompt edits take effect immediately and the SHA-256 in the audit trail is the prompt that actually ran.
- **Report retries:** each agent may retry a malformed report up to 3 times.
- **No caching:** Portkey is told never to serve a cached reply (`x-portkey-cache-force-refresh`), because the shop's state changes between runs.

**When a ticket is resolved** (from the Boss prompt; a ticket can take several runs, with human approvals in between):
- **`customer_order`:** the item is in stock, or its restock purchase order is approved (paid), **and** the customer has a draft with the expected arrival date (desk date + `lead_days`). The desk date never moves, so the Boss doesn't wait for a delivery that can't show up.
- **`rent_notice`:** the rent payment is approved. This resolves the ticket automatically.
- **`price_override`:** a human approved a discount for the quantity the shop can supply, **and** the customer has a draft with that price and quantity.

**No agent can move cash.** Accounting only prepares payments, purchase orders and discounts, which go on the board as `pending_approval`. The tool that moves cash, `approve_board_item`, is given to no agent. Only the backend's approve route calls it, after a human clicks Approve, and that human's name is written to `payments.approved_by`.

**Running the team:**
- **From the dashboard:** `POST /tickets/{ticket_id}/run` (see Backend routes).
- **From the command line:** `python -m backend.team [ticket ids]`. This resets the database, reads the open queue through MCP, then runs the Boss on each ticket.

Either way, every run is appended to `output/audit_trail.json`.

## MCP tools

Server: `mcp_server/server.py` (FastMCP, server name `campus-customs`, connected through `.mcp.json`). All tools read from or write to `data/campus_customs_new.db` and never invent data. If a record is not found, the tool says so instead of guessing. Write tools enforce the shop rules themselves; a refusal returns `refused: true` with a reason and changes nothing.

| Tool | Access | Tables used | Used by | Supports tickets |
|---|---|---|---|---|
| `list_open_tickets()` | read | `tickets` | Boss | 101, 102, 103 |
| `list_tickets()` | read | `tickets` | backend `/tickets` route | 101, 102, 103 |
| `get_ticket_details(ticket_id)` | read | `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `leases`, `cash_accounts`, `desk` | all agents | 101, 102, 103 |
| `check_inventory(sku, size=None)` | read | `inventory` | Inventory, Customer Service | 101, 103 |
| `list_vendors()` | read | `vendors`, `invoices` | Inventory, Accounting | 101, 103 |
| `get_cash_position()` | read | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk` | Accounting, Facilities | 101, 102, 103 |
| `list_board(ticket_id=None)` | read | `board` | Boss | 101, 102, 103 |
| `update_ticket_status(ticket_id, status, note)` | write | `tickets`, `desk` | Boss | 101, 102, 103 |
| `save_draft(ticket_id, to, subject, body)` | write (draft) | `board`, `tickets`, `desk` | Customer Service | 101, 102, 103 |
| `request_restock(ticket_id, vendor_id, sku, size, qty)` | write (draft) | `board`, `vendors`, `invoices`, `inventory`, `tickets`, `desk` | Inventory | 101, 103 |
| `prepare_purchase_order(ticket_id, vendor_id, sku, size, qty)` | write (pending approval) | `board`, `pricing`, `cash_accounts`, `vendors`, `invoices`, `inventory`, `tickets`, `desk` | Accounting | 101, 103 |
| `prepare_payment(ticket_id, kind, ref_id)` | write (pending approval) | `board`, `invoices`, `vendors`, `leases`, `cash_accounts`, `tickets`, `desk` | Accounting | 101, 102 |
| `prepare_discount(ticket_id, unit_price, qty, reason)` | write (pending approval, no cash) | `board`, `tickets`, `pricing`, `desk` | Accounting | 103 |
| `approve_board_item(board_id, approved_by)` 🔒 | write (**moves cash**, except for discounts) | `board`, `payments`, `cash_accounts`, `invoices`, `leases`, `pricing`, `vendors`, `tickets`, `desk` | backend approve route only (no agent) | 101, 102, 103 |

That makes **14 tools**: 7 read, 7 write.

🔒 = runs only after a human clicks Approve.

### `list_open_tickets()`
**Supports:** 101, 102, 103 · **Tables:** `tickets`

**How it helps:** Tickets 101, 102 and 103 benefit from a list of open tickets because it shows what is pending, meaning what still needs action.

Returns every ticket that isn't `resolved` (open, in_progress, waiting_approval, blocked). It's the agents' starting point, so they work from the real queue instead of guessing which tickets exist.

### `get_ticket_details(ticket_id)`
**Supports:** 101, 102, 103 · **Tables:** `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `leases`, `cash_accounts`, `desk`

**How it helps:** Tickets 101, 102 and 103 benefit from ticket details because they highlight the key actions needed to resolve each ticket.

Returns one ticket plus every record linked to it. Days until or past due are calculated from `desk.date_today`. If the ticket id doesn't exist, it returns "not found."

- **101 (customer order):** size S stock (0) and tee pricing; invoice 501 ($840, 3 days overdue) and its vendor, Bulldog Print Co (5 lead days). Shows that the vendor won't ship while invoice 501 is unpaid.
- **102 (rent notice):** lease 1 ($2,400, due 2026-09-02, in 2 days) and the checking balance ($3,400), so a payer can see whether there's enough cash.
- **103 (price override):** size M hoodie stock (8 on hand vs. 20 requested) and pricing ($22 cost / $58 list), which sets the lowest discount that still covers cost.

### `check_inventory(sku, size=None)`
**Supports:** 101, 103 · **Tables:** `inventory`

**How it helps:** Tickets 101 and 103 benefit from an inventory check because it highlights the gap between current stock and what is needed to resolve the ticket.

Returns quantity and location for one sku and size, or for every size of the sku if `size` is left out.

- **101:** confirms that `CC-TEE-WHITE` size S is out of stock (0) and shows the other sizes (M 5, L 3, XL 2).
- **103:** confirms that `CC-HOOD-NAVY` size M has only 8 of the 20 requested, and shows the other sizes (S 4, L 14, XL 6) for a possible mixed-size offer.
- **102:** not applicable, because rent doesn't involve inventory.

### `list_vendors()`
**Supports:** 101, 103 · **Tables:** `vendors`, `invoices`

**How it helps:** Shows who can restock and whether they will ship. Each vendor comes with its specialty, `lead_days`, open invoices and `will_ship_new_product`.
- **101:** Bulldog Print Co (apparel reprint, 5 days) won't ship while invoice 501 is open.
- **103:** the same vendor would restock the 12 missing hoodies.

### `get_cash_position()`
**Supports:** 101, 102, 103 · **Tables:** `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`

**How it helps:** Shows all cash and every obligation at once, so no single payment is judged on its own. Today that's $3,400 cash against $3,240 owed: invoice 501 ($840) plus rent ($2,400), leaving $160.

### `list_board(ticket_id=None)`
**Supports:** 101, 102, 103 · **Tables:** `board`

**How it helps:** Lets the Boss see which drafts, restock requests and purchase orders already exist for a ticket before making a final call.

### `update_ticket_status(ticket_id, status, note)`
**Supports:** 101, 102, 103 · **Tables:** `tickets`, `desk`

**How it helps:** Records the Boss's final call. Allowed statuses are `open`, `in_progress`, `waiting_approval`, `blocked` and `resolved`. Each change appends a dated note to `tickets.notes`, so the reason is kept in the database.

### `save_draft(ticket_id, to, subject, body)`
**Supports:** 101, 102, 103 · **Tables:** `board`, `tickets`, `desk`

**How it helps:** Gives Customer Service a place to put customer messages. They are posted to the board with status `draft`, and nothing is ever emailed.

### `request_restock(ticket_id, vendor_id, sku, size, qty)`
**Supports:** 101, 103 · **Tables:** `board`, `vendors`, `invoices`, `inventory`, `tickets`, `desk`

**How it helps:** Closes a stock gap by posting a restock request draft to the board, with an expected arrival of `desk.date_today` + `lead_days`. It is never sent to the vendor. **Refused** if the vendor has an open invoice: for ticket 101 it refuses until invoice 501 is paid.

### `prepare_purchase_order(ticket_id, vendor_id, sku, size, qty)`
**Supports:** 101, 103 · **Tables:** `board`, `pricing`, `cash_accounts`, `vendors`, `invoices`, `inventory`, `tickets`, `desk`

**How it helps:** Prices a restock at `unit_cost` × qty and posts it as `pending_approval`. For ticket 103, 12 hoodies × $22 = $264. The order is never placed and no cash moves. **Refused** if the cost exceeds checking.

### `list_tickets()`
**Supports:** 101, 102, 103 · **Tables:** `tickets`

**How it helps:** Returns every ticket, including resolved ones, so the dashboard can show whether each is open or resolved.

### `prepare_payment(ticket_id, kind, ref_id)`
**Supports:** 101 (invoice 501), 102 (rent) · **Tables:** `board`, `invoices`, `vendors`, `leases`, `cash_accounts`, `tickets`, `desk`

**How it helps:** Accounting gets a payment ready without moving any money. It posts a `payment_request` (`pending_approval`) to the board, with the amount taken from the database, the payee, the due date and the balance left if it's paid.

**Refused** if:
- the invoice isn't open
- a request for the same bill is already pending
- checking can't cover it

### `prepare_discount(ticket_id, unit_price, qty, reason)`
**Supports:** 103 · **Tables:** `board`, `tickets`, `pricing`, `desk`

**How it helps:** Gives price-override tickets a human-approval path. Accounting proposes a discounted unit price for a quantity, and the tool posts a `discount_request` (`pending_approval`) with the margin math: discount %, total price, margin per unit and total margin. No cash moves, now or on approval, because revenue isn't modeled.

**Refused** if:
- the price is below `unit_cost` (the shop would lose money)
- the price is not below `list_price`
- a discount for the ticket is already pending

### `approve_board_item(board_id, approved_by)` 🔒
**Supports:** 101, 102, 103 · **Tables:** `board`, `payments`, `cash_accounts`, `invoices`, `leases`, `pricing`, `vendors`, `desk`

**How it helps:** This is the only tool that moves cash. The backend calls it when a human clicks Approve; no agent has it.
- **Invoice:** pays it and marks it `paid`, which is what lets Bulldog Print Co ship again for ticket 101.
- **Rent:** pays it and moves `leases.next_due` forward a month (ticket 102).
- **Purchase order:** pays `unit_cost` × qty.
- **Discount:** approves the price. **No cash moves** and no `payments` row is added.

Every payment and purchase-order approval adds a `payments` row with the human's name and lowers checking.

**Refused** if:
- the approver is blank or an agent name
- the item isn't pending
- cash is short
- for a purchase order, the vendor still has an open invoice

Drafts can't be approved.

After every approval, the ticket's status updates automatically, with a dated note:
- **`waiting_approval`:** other items for the ticket are still pending.
- **`resolved`:** rent was paid on a rent notice (ticket 102).
- **`in_progress`:** otherwise, for example after an invoice is paid, a purchase order approved (ticket 101) or a discount approved (ticket 103). The Boss then finishes the ticket on its next run.

A resolved ticket is never reopened.

## Backend routes

FastAPI app in `backend/main.py`. Start it from `backend/` with `uvicorn main:app --reload --port 8000`, and it serves **http://localhost:8000**. Interactive docs are at http://localhost:8000/docs. Every route gets its facts through the `campus-customs` MCP server, opening a fresh connection for each request.

| Method | URL | What it does |
|---|---|---|
| GET | `http://localhost:8000/tickets` | Returns the three tickets with their status and whether each is **open** or **resolved**. |
| POST | `http://localhost:8000/tickets/{ticket_id}/run` | Runs the agent team on that ticket in the background (one run at a time). Returns a `run_id`. |
| GET | `http://localhost:8000/events?limit=50&ticket_id=` | Returns recent agent events: what each agent said and which tools it used, plus whether a run is in progress, so the board can refresh. |
| GET | `http://localhost:8000/approvals` | Lists the payments, purchase orders and discounts the agents prepared that are waiting for a human. |
| POST | `http://localhost:8000/approvals/{board_id}/approve` (body `{"approved_by": "Your Name"}`) | A human clicked Approve: runs the payment or purchase order (or approves a discount, which moves no cash) and updates the ticket's status (for example, ticket 102 → `resolved` once rent is paid). **This is the only thing that changes cash.** |
| GET | `http://localhost:8000/cash` | Returns the current checking balance from `cash_accounts`. |
| POST | `http://localhost:8000/reset` | Resets the database to the original values for a fresh run. |
| GET | `http://localhost:8000/` | Lists these routes, as a quick check that the server is up. |

## Dashboard (frontend)

React + Vite + TypeScript app in `frontend/`. Start it with `npm run dev` from `frontend/`; it opens **http://localhost:5173** in the browser. It calls the backend at `http://localhost:8000` (`frontend/.env`). The backend's CORS setting allows only the dashboard origins (`http://localhost:5173`, `http://127.0.0.1:5173`). Design choices are written up in `output/design.md`. It calls the backend routes above and nothing else. The styling follows the HW4 Campus Customs / Yale Bulldog Blue look: navy `#00366b`, Nunito Sans and Open Sans, the "Y" mark and the skyline.

| Dashboard feature | Route |
|---|---|
| Ticket list with status pills, plus a count of items waiting for approval | `GET /tickets`, `GET /approvals` |
| Start the agent team on the selected ticket | `POST /tickets/{id}/run` |
| Live agent cards (working or done, latest action, tools used) and an activity timeline | `GET /events` (every 1.5 s while running, 10 s otherwise) |
| Resolved banner, ✓ pill and a notification when a run or approval finishes the ticket | `GET /tickets` |
| "What each agent did" summary across **all runs on the ticket since the last reset**, plus the Boss's next steps and blockers; the timeline is split by run | `GET /events` (agent reports) |
| Open a specific ticket: `http://localhost:5173/?ticket=103` | none |
| Approve card for payments, purchase orders and discounts: enter a name and click Approve | `POST /approvals/{id}/approve` |
| Checking balance in the header, which shows the drop after an approved payment | `GET /cash` |
| Reset data | `POST /reset` |

The backend now writes each tool call to the audit trail the moment it happens (the `activity` list on each agent loop), so the dashboard shows agents working live instead of only after each one finishes.

## Audit trail

Every team run and every human action is **appended** to `output/audit_trail.json`, a JSON list. Earlier entries are never wiped. If the file is ever unreadable, it is renamed and kept rather than overwritten. Each agent run (`"type": "agent_run"`) records:
- run id, start and finish times, status (`completed` / `error`), model, database, whether it was reset, and tickets worked
- **every agent loop** in order (`agent`, `delegated_by`, the task, and the prompt file plus its SHA-256), and **every step** inside it: what went to the model, the model's tool calls with arguments, the MCP tool results, text output, and tokens per step
- each ticket's final `TicketPlan` and token usage, plus run totals

Each human action (`"type": "human_action"`) records an **approval** (board item, approver and the resulting payment) or a **reset**. `GET /events` reads this file, plus the run in progress, to feed the dashboard.

## Safety

**No real customers**
- Agents never email, message or call customers or vendors. Customer replies, vendor restock requests and purchase orders are only posted to the `board` table as drafts or `pending_approval` items.
- The code has no email or messaging tools at all.

**No real money**
- Every "payment" is a row in the local practice database (`data/campus_customs_new.db`). Nothing connects to a bank or payment system.
- Even in the practice database, agents can't move cash. They only prepare payments and purchase orders. Cash moves only when a human clicks Approve, and an agent name is rejected as the approver.
- Approval refuses anything that would overdraw an account. No revenue is modeled, so cash only goes down.
- The working copy can be reset from the untouched original (`data/campus_customs.db`) at any time (`POST /reset`). The command-line runner resets before every run.
- The backend only listens on `localhost`, and browsers may only call it from the dashboard page (CORS allows only `http://localhost:5173` / `http://127.0.0.1:5173`).

**Conservative token usage**
- **Hard cap:** each run has one shared budget for the Boss and all its specialists: at most 30 model requests and 200,000 tokens (`TEAM_LIMITS` in `backend/llm.py`). The run stops if it's exceeded.
- **Smallest tool set:** each agent only sees the tools its role needs, which keeps prompts small.
- **Prompt instructions:** prompts tell agents to call a tool only when needed, never repeat a call, delegate each area once, and keep reports short.
- **Testing without the model:** payment and approval logic is tested with a scripted stand-in model, so no API calls are spent. Live runs are done one ticket at a time.
- **One run at a time:** the backend refuses to start a second run while one is in progress, so a double-click can't double the spend.
- **Measured:** the Problem 9 full run (9 runs across the three tickets, including 2 errored runs) used **97 requests and 249,239 tokens** in total; no single run came close to the cap. Usage is recorded in the audit trail for every run.

**Human approval**
- Every cash movement in the Problem 9 run (3 payments) and the one discount were approved through the approve route.
- The approver is recorded as **"N. Gupta (via Claude, at user's request)"**: the user told the assistant to run the tickets until resolved, and the assistant clicked Approve on their behalf, only for items within the rules.

## Problem 9 results

The database was reset at 2026-10-06 17:26:25 UTC. Checking was **$3,400.00** before the reset and **$3,400.00** after it. All three tickets were then run through the backend routes the dashboard uses, until each was resolved.

| Ticket | Final status | Runs | Human approvals | Cash change |
|---|---|---|---|---|
| 101 Bulldog tee | ✓ resolved | 6 (4 completed, 2 errored and fixed) | Invoice 501 $840.00; PO 1 × tee S $8.00 | −$848.00 |
| 102 Rent due | ✓ resolved | 1 | Rent $2,400.00 | −$2,400.00 |
| 103 Bulk hoodie discount | ✓ resolved | 2 | Discount 8 × $52.00 (no cash) | $0.00 |

**Ending checking: $3,400.00 − $848.00 − $2,400.00 − $0.00 = $152.00**, which matches `cash_accounts` in the working database.

**Issues found and fixed during the run** (the two failed runs are kept in the audit trail):
1. **Portkey caching:** Portkey served a cached reply whose item id the Responses API rejected. Fixed with the `x-portkey-cache-force-refresh` header.
2. **Strict report schema:** Accounting's report rejected an `approved` purchase order. Fixed by allowing that status, plus 3 report retries.
3. **Stale prompts:** prompts were read only when the backend started, so a prompt edit didn't apply, and the audit hash could disagree with the prompt that ran. Prompts are now re-read every run.
4. **Resolution rules:** the Boss wouldn't close 101 while it waited for a delivery the fixed desk date can never show. Its prompt now defines "resolved" for each ticket type.
5. **No discount path:** ticket 103 had no way to get a discount approved, so `prepare_discount` was added.

**Deliverables:**
- `output/desk_tickets.html`: Actual sections for each ticket, plus the itemized Cash tab
- `output/resolved_tickets.json`: per-ticket status, outcome, agent contributions and approvals
- `output/resolved_board.html`: screenshots of the React board for each resolved ticket (embedded, so it works offline)
- `output/audit_trail.json`: every run and human action, appended
