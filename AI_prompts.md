# AI Prompts Log — HW5: Campus Customs Multi-Agent Operations

This file logs every prompt sent to the AI coding assistant, grouped by problem.
Each section lists the initial prompt(s) and any follow-up prompts. For each
follow-up, it notes what was missing from the earlier prompt that made the
follow-up necessary.

---

## Setup (before Problem 1)

### Prompt 1
> Hey we're working in HW 5 in the AI folder. Can you wipe out everything that is there right now?

**Result:** The assistant listed the folder contents and asked how much to delete. The user chose "Everything," and the HW5 folder was emptied.

### Prompt 2
> HW 5 is about supporting the agentic team for Campus Customs Multi-Agent Operations. The purpose of this assignment is to support open tickets for activities like customer orders, rent, unpaid bills, discount requests, and whatever the shop needs to handle. To start let's unzip the attached file. The file includes the original shop database with tables for desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, and invoices. Let's make a copy of the data base and call is data/campus_customs_new.db.

**Result:** Unzipped `data/campus_customs.db` and copied it to `data/campus_customs_new.db`. Both copies passed an integrity check and have the same row counts.

### Follow-up prompts
None.

---

## Problem 1 — Viber coder prompts

### Prompt 1
> No let's just go into the problems to start. Let's start with Problem 1 (titled 'Viber coder prompts'). Create an AI_prompts.md. This will log our dialogue. Let's make sure it is set up so there is a section for each problem number/title, include all the prompts I send you, follow up prompts I send you, and explain what was lacking to need a follow up prompt

**Result:** Created this file, with a section for each problem, verbatim prompts, follow-ups, and an explanation of each follow-up.

### Follow-up prompts
None.

---

## Problem 2 — Open tickets and how they connect to the tables

### Prompt 1
> Great, let's go to Problem 2. Let's confirm that we have made our working copy of the data file (data/campus_customs_new.db). Can you tell me the three open tickets indicated in the data set and explain how they are connected to the tables indicated in the set?

**Result:** Confirmed that `data/campus_customs_new.db` exists. Read the schema and every row, then explained tickets 101 (customer order), 102 (rent notice) and 103 (price override), and how each one connects to inventory, pricing, invoices, vendors, leases, cash_accounts, payments and desk.

### Prompt 2
> Let's now create an output/harness.md. In this, let's start by including for each table, the listed fields. Let's also include a short line as to why that table matters for us for this assignment. For inventory, indicate that it is important as it tells us stock availability. For pricing, include that it is importance since it tells how much items will cost. For invoices, indicate that its important because it tells us transactions that have occurred. For vendors, indicate that it tell us who is providing our inventory. For payments/ cash_accounts, indicate that this supports our understanding of cash flow. For leases, indicate that this tell us existing physical locations and cash flow.

**Result:** Created `output/harness.md` with a field table and a "why it matters" line for all 9 tables. Used the user's wording for the 7 tables they described. The assistant wrote short lines for `desk` and `tickets`, which the prompt didn't cover.

### Follow-up 1
> Okay we can update that to be more accurate

**What was lacking:** Prompt 2 described invoices as "transactions that have occurred." Invoices are actually bills the shop owes. Invoice 501 is still `open`, so it is unpaid, and finished transactions go in `payments`. The assistant pointed this out, and the follow-up approved the correction.

**Result:** Changed the invoices line in `output/harness.md` to say that invoices tell us what we owe vendors and when it is due, and that completed payments are recorded in `payments`.

### Prompt 3
> Great, as we go forward in the assignment I'd like to flag a few rules that we will need to be aware of. The field desk.date_today indicates that literally today (10/6/2026) is the date that we measure 'overdues' off of. Vendor lead times will come from vendors table. Vendor will not ship new products if they have an open unpaid invoice. Human approval is needed for payments and the relevant table should be updated when this occurs. If there is not enough cash, the pay tool must refuse, there are no negative balances. Cash only goes out, we do not model revenue so no money is coming in. Before resolving tickets, make sure to reset the database to original values. Do not email customers or call real vendors they drafts stay on the board. We also need to be working only with gpt-6-luna.

**Result:** Added an "Operating rules" section to `output/harness.md` with the 9 rules. Asked the user to clarify two things: the database stores `desk.date_today = 2026-08-31`, not 10/6/2026, and the assistant could not confirm that the model ID `gpt-6-luna` exists.

### Follow-up 2
> (Clarification answer) Use database value — treat `desk.date_today` exactly as stored (2026-08-31).

**What was lacking:** Prompt 3 said `desk.date_today` meant "literally today (10/6/2026)," but the stored value is 2026-08-31. The two dates give very different overdue results: rent would be due in 2 days under one and 34 days overdue under the other. The prompt had to say which date counts.

**Result:** Rule 1 in `output/harness.md` now says to use `desk.date_today` exactly as stored (2026-08-31) for all overdue checks.

### Follow-up 3
> We are using PORTKEY_API_KEY

**What was lacking:** Prompt 3 named the model (`gpt-6-luna`) but not how to reach it. Without the provider or gateway and the credentials, the assistant could not set up agents to call it.

**Result:** Confirmed that `PORTKEY_API_KEY` is set in the environment (the value was not printed). Updated rule 9 in `output/harness.md`: `gpt-6-luna` is called through the Portkey gateway, and the key is read from the environment variable and never hard-coded.

---

## Problem 3 — Build the MCP server

### Prompt 1
> Okay let's get to Problem 3 (titled Build the MCP server). Write an MCP Server in mcp_server/ using FastMCP. This will talk to the data/campus_customs_new.db. We don't need to connect or run it yet for this problem. We will use MCP server throughout this assignment, but we will ad more tools to it. :et's make sure we are not inventing any data and information comes from the database. Can you suggest three tools to add to the server that will help for tickets in the database?

**Result:** Created `mcp_server/__init__.py` and `mcp_server/server.py`. The server is a FastMCP app named `campus-customs` with a database connection helper. The helper points at `data/campus_customs_new.db` and refuses to run if the file is missing, so it can't quietly create an empty database. No tools yet. The assistant suggested three read-only ticket tools: `list_open_tickets`, `get_ticket_details` and `check_inventory`. The server was not run (FastMCP isn't installed yet); a syntax check passed.

### Prompt 2
> Great, let's include the three suggested tools in an output/harness.md. Let's make sure each tool is tagged to the ticket it will help support (101, 102, 103).

**Result:** Added an "MCP tools" section to `output/harness.md`, with a summary table and a section for each tool. Each tool is tagged with the tickets it supports: `list_open_tickets` → 101/102/103, `get_ticket_details` → 101/102/103, `check_inventory` → 101/103. Each section explains how the tool helps each ticket and which tables it reads. The tools are documented only; they are not yet written in `server.py`.

### Prompt 3
> Include the following descriptions into the output/harness.md. 101/102/103 benefit from listing open tickets as it indicates to us what is 'pending' or needs action taken. get ticket details benefits 101/102/103 as it highlights the key actions needed to be taken to resolve tickets. And check inventory benefits 101/103 as it highlights the gap between current status and resolution of ticket.

**Result:** Added a "How it helps" line in the user's words under each tool in `output/harness.md`. The existing ticket-by-ticket details were kept.

### Follow-up prompts
None.

---

## Problem 4 — Add the MCP server to vibe coder and test each tool

### Prompt 1
> Great, let's go to problem (titled Add the MCP server to vibe coder and test each tool) Let's add the MCP server to this project so that you are able to call all the tools. We will save this connect as a JSON text in .mcp.json at the project root. Let's then test the three MCP tools we created. Save the evidence of this test in output/mcp_smoke.json. For each tool test, include the prompt I asked you, the tool's name, and the output from the tool (it must match values from our working copy database).

**Result:**
- Wrote the three tools in `mcp_server/server.py`. They were only described before.
- Created `.venv`, installed FastMCP 4.0.11 and saved `requirements.txt`.
- Created `.mcp.json` at the project root. It registers `campus-customs` as a stdio server using `.venv`'s Python.
- Ran a smoke test that starts the server exactly as `.mcp.json` describes. It calls `list_open_tickets`, `get_ticket_details` (101, 102, 103) and `check_inventory` (tee S, hoodie M, all hoodie sizes) and compares every output against direct SQL queries on `data/campus_customs_new.db`. All 7 calls matched.
- Saved the evidence to `output/mcp_smoke.json`. Each test records the prompt, tool name, arguments, output and the field-by-field database check.

**Note:** The problem title doesn't include a number. Logged here as Problem 4, the next in sequence.

### Follow-up prompts
None.

---

## Problem 5 — Build the agent team and grow the MCP tools

### Prompt 1
> Great, let's go to Problem 5 (titled Build the agent team and grow the MCP tools). We are now going to build the agentic team for Campus Customs using the PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. We will need to include prompts, models, and agent loops for each so we can delegate work to each and support full connectivity. Let's put prompts in backend/prompts/ (ensure only one file per agent). Put data types in in backend/models.py and the agent files under backend/ (ensure all 5 roles are clear). Make sure PORTKEY_API_KEY and only gpt-5-luna for each agent.

**Result:** Before building, the assistant asked which model to use, because this prompt says `gpt-5-luna` but rule 9 says `gpt-6-luna` (see Follow-up 1). Then it built:
- `backend/prompts/`: one prompt file per agent (`boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md`). Each includes the shop rules.
- `backend/models.py`: data types: `TicketPlan` and `Delegation` (Boss), `InventoryReport`, `AccountingReport`, `FacilitiesReport` and `CustomerDraft`.
- One agent file per role: `backend/boss.py`, `inventory.py`, `accounting.py`, `facilities.py`, `customer_service.py`. Each has a PydanticAI agent and a `run_<role>()` loop. The Boss delegates through the `ask_inventory`, `ask_accounting`, `ask_facilities` and `ask_customer_service` tools.
- `backend/llm.py`: the single place the model is set (`gpt-6-luna` via Portkey, using `PORTKEY_API_KEY`). It also connects each agent to the MCP server through `.mcp.json`.
- `backend/main.py`: the team loop. It resets the database (rule 7), then the Boss works each open ticket.

A test call confirmed that `gpt-6-luna` works through Portkey. The first full run failed: the provider rejects tool calls for this model on the Chat Completions endpoint. The assistant switched to the Responses API. Ticket 102 then ran end to end, with the Boss delegating to Facilities, Accounting and Customer Service.

### Follow-up 1
> (Clarification answer) gpt-6-luna

**What was lacking:** The prompt said `gpt-5-luna`, which conflicts with rule 9 from Problem 2 (`gpt-6-luna`). The assistant couldn't tell which was right, so the model name had to be confirmed. It was a typo; all agents use `gpt-6-luna`.

**Result:** Rule 9 is unchanged. Every agent uses `gpt-6-luna`.

### Follow-up 2
> Before we do that, I need to provide the prompts for the agents. They are as follows: Boss - reads each ticket, decides who should work on it, and makes final calls. Inventory - checks stock by SKY and size, spots shortfalls, and figures out which vendor can restock. Accounting - watches cash, and invoices, checks margins, and prepare payments or purchases orders for human approval. Facilities - handles the shop space side (leases, rent, etc.). Customer Service - drafts messages for customers. Can you make sure the prompts are updated?

**What was lacking:** Prompt 1 asked for prompts per agent but did not define each role, so the assistant wrote its own role descriptions. This follow-up supplies the intended role for each agent. It also adds a duty the first version didn't have: Accounting prepares **purchase orders** for human approval.

**Result:**
- Each file in `backend/prompts/` now has a "Role" section in the user's wording. "SKY" was read as SKU.
- The Boss's team list was updated to match.
- The Boss prompt notes that "final calls" can't override the human-approval rule.
- Inventory now chooses the restock vendor by matching `vendors.specialty`.
- Accounting has a purchase order duty, backed by a new `PurchaseOrder` type in `backend/models.py` (status `pending_approval`) and an optional `purchase_order` field on `AccountingReport`.

### Prompt 2
> Yes let's go ahead with the tools you suggested. Let's make sure these tools help us with working on open tickets. Make sure all facts are only coming from the MCP Server over data/campus_customs_new.db. Do not invent second shop tools layer that bypasses the MCP. Let's also wire the agents so they append to output/audit_trail.json for each run including each agent-loop step, record enough to audit later. Append this file do not wipe it each run. Let's also in output/harness.md, list each agent and each MCP tool (including the ones added in this problem) along with the table the tool uses. Let's also include a safety section where its clear that we are not touching real customers, real money, and we are conservative with token usage. Make sure the mcp_server/README.md matches with the tool list and what we have now.

**Result:**
- **MCP server** (`mcp_server/server.py`, still the only code that touches the database): grew from 3 tools to 12.
  - Read tools: `list_vendors`, `get_cash_position`, `list_board`.
  - Write tools: `update_ticket_status`, `save_draft`, `request_restock`, `prepare_purchase_order`, `pay_invoice`, `pay_rent`.
  - The write tools enforce the rules themselves: a human approver is required, there are no negative balances, a vendor with an open invoice won't ship, and messages are drafts only (posted to a new `board` table).
  - `list_open_tickets` now returns every ticket that isn't resolved.
- **Agents:**
  - Each agent gets only its role's tools.
  - `pay_invoice` and `pay_rent` pause for human approval at the terminal, and the human's name overrides whatever the model sent. With no human present, payments are denied.
  - A per-ticket token budget is shared by the Boss and its specialists (30 requests / 200k tokens).
  - The prompts were updated with the new tools, how to handle refusals, and token economy.
- **Audit trail** (`backend/audit.py`): each run is appended to `output/audit_trail.json`. It records every agent loop and step (tool calls, arguments, results, tokens), every approval decision, prompt hashes, and the result and usage for each ticket. Writes are atomic, and an unreadable file is kept rather than wiped.
- **Docs:**
  - `output/harness.md`: added the `board` table, an Agents section, a table of all 12 MCP tools with the tables each uses, an Audit trail section and a Safety section (no real customers, no real money, conservative token use).
  - `mcp_server/README.md`: written to match. A script confirmed that both docs list exactly the server's 12 tools.
- **Testing:**
  - All 12 tools and every refusal case were tested over MCP: 17/17 passed, and the database was reset afterward.
  - Approval was tested with a scripted model, no tokens used: denied left the database unchanged; approved recorded the human's name.
  - The first live run of ticket 101 crashed on Windows: an empty input looked like a terminal, so the approval prompt waited for typing that never came. This was fixed, and the crashed run stays in the audit trail as `error`.
  - The second live run completed: 14 requests and about 30.6k tokens. The payment was denied (no human present), ticket 101 was set to `blocked`, and a purchase order and a customer draft were posted to the board.

### Follow-up prompts
None.

---

## Problem 6 — Plan the three tickets

### Prompt 1
> Let's do Problem 6 (titled Plan the three tickets). We're going to track what we expect each team to do with the open tickets. Let's create output/desk_tickets_html - this page should be able to accessed by double clicking it. I need one tab per ticket (101 / 102/ 103). Let's also add empty tabs for cash and reflection (we will populate in future problems). On each ticket tab let's fill an expected section, but let's leave room for an actual section that will be populated after we run the agents. For ticket 101 expected section, please indicate that 'Boss' should call vendor first to see if they are anticipating new inventory for the shirt customer is looking to order before cancelling order / potential income. Boss will delegate to vendor to flag what is upcoming and update if the inventory can expect to carry the item to be ordered. check inventory MCP tool via sku would likely be used. For ticket 102, Boss will call facilities to track rent notice and plan for payment given it is due in 2 days. Agent will delegate to facilities who will then delegate to accounting to track inflow and outflow of cash for the purposes of rent and ensure financial statements for store are accurate. Cash accounts and payments will likely be called for the MCP tools. For ticket 103, Boss will likely call call accounting to track the impact and possibility of providing a bulk discount without hurting the finances of the store. From Accounting this will likely delegate to customer service to customer if Boss and Accounting approve this decision or not. Pricing is likely the MCP tool to call.

**Result:**
- Created `output/desk_tickets.html`, read as `desk_tickets.html`; the prompt wrote `desk_tickets_html`. It is a single self-contained file with no server or internet needed, so it opens with a double-click.
- Five tabs: 101, 102, 103, Cash and Reflection. Cash and Reflection are empty placeholders.
- Each ticket tab has the ticket's facts from the database, an **Expected** section in the user's words (lead, delegation flow, likely MCP tools), and an empty **Actual** section for after the agents run.
- Each Expected section also has a short "How this maps to our harness" note. These flag where the expectation differs from the current design:
  - There's no vendor agent, and vendors are never contacted (rule 8).
  - Specialists report to the Boss and don't delegate to each other.
  - "Cash accounts," "payments" and "pricing" are tables, reached through MCP tools (`get_cash_position`, `pay_rent`, `get_ticket_details`).
  - No inflow is modeled.
  - Price overrides need human approval.
  - The user's expectations themselves were not changed.

### Follow-up prompts
None.

---

## Problem 7 — Backend routes

### Prompt 1
> Let's go to Problem 7 (titled Backend routes). We need to create backend/main.py use FastAPI and add routes that do the following: Return the three tickets and whether each is open or resolved, Take a ticket id and run your agent team on that ticket, Return recent agent events - what each agent said and which tools they used - so the board can refresh, Approve a payment or purchase after a human clicks approve (I know you can prepare the pya, but the route is what will actually change the cash), Return the current checking balance from cash_accounts,Reset the database the original values when we need to try a fresh run. From backend/ lets start with the server uvicorn main:app --reload --port 8000. This will turn on your backend at http://localhost:8000, so the frontend dashboard can call those routes. In output/ harness.md, least each route in one (what the URL is / what it does).

**Result:**
- **`backend/main.py`** is now a FastAPI app with these routes:
  - `GET /tickets`
  - `POST /tickets/{id}/run`: runs in the background, one run at a time.
  - `GET /events`
  - `GET /approvals`
  - `POST /approvals/{board_id}/approve`
  - `GET /cash`
  - `POST /reset`
  - `GET /`: lists the routes.

  All facts come through the MCP server. The old command-line team loop moved to `backend/team.py`.
- **Payment flow redesign.** The prompt said the route, not the agent, should change the cash, so:
  - **Removed:** the MCP tools `pay_invoice`, `pay_rent` and the terminal approval prompt.
  - **Added:** `prepare_payment`, used by Accounting, which posts a `payment_request` to the board with no cash moving.
  - **Added:** `approve_board_item`, which no agent has. Only the approve route calls it. It pays invoices, rent or purchase orders under the human's name, and refuses agent names, shortfalls, and purchase orders while the vendor has an unpaid invoice.
  - **Added:** `list_tickets`, for the `/tickets` route.
  - The server now has 13 tools.
- **Audit trail:** also records human actions (approvals and resets). `/events` turns the trail plus the run in progress into events: `tool_call`, `tool_result`, `said`, `report`, `human_action`.
- **Server:** started from `backend/` with `uvicorn main:app --reload --port 8000`.
- **Testing:**
  - Every route was tested.
  - Ticket 102 ran live through the API. Accounting prepared the $2,400 rent payment, and a second run request during it got a 409.
  - Approving as "accounting" was refused. Approving as "Test Human" moved checking from $3,400 to $1,000. Approving twice was refused. Reset restored $3,400.
  - The purchase order and invoice approval paths were tested over MCP.
- **Docs:**
  - `output/harness.md`: new "Backend routes" table (URL / what it does). Updated the Agents, MCP tools, Audit trail and Safety sections.
  - `mcp_server/README.md`: updated to match. Both docs were checked against the server's 13 tools.

### Follow-up 1
> Yes let's include that as well

(Reply to the assistant's question: should approving a payment also update the ticket's status automatically?)

**What was lacking:** Prompt 1 asked for an approve route that changes cash, but didn't say what should happen to the ticket afterwards. So after a payment was approved, ticket 102 stayed at `waiting_approval` even though the rent was paid. `/tickets` would never show it as resolved unless the agents ran again.

**Result:**
- `approve_board_item` now updates the ticket after each approval, with a dated note:
  - `waiting_approval` if other items for the ticket are still pending
  - `resolved` once rent is paid on a rent notice
  - `in_progress` otherwise, e.g. invoice paid or purchase order approved
  - It never reopens a resolved ticket.
- Tested over MCP (101: waiting_approval → in_progress; 102: resolved) and through the routes: approving the rent showed ticket 102 as `resolved` on `/tickets`.
- While testing, uvicorn's `--reload` stalled on Windows because the backend held a persistent MCP connection. The backend now opens a fresh MCP connection per request (about 2 seconds per call), which also means server changes apply immediately.
- The harness and README were updated.

---

## Problem 8 — Agent Dashboard

### Prompt 1
> Let's do Problem 8 now. It is titled Agent Dashboard. Build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes we built in Problem 7. The board should do at minimum the following activities: List all three tickets, Let you pick one ticket and start the agent team on it, Show each agent and what they are saying/ doing while the ticket runs, Mark a ticket resolved when the run finishes, Show a short summary of what each agent did on that ticket, let a human approve a pay or purchase when asked,  show the checking balance (It should drop after an approved pay). Let's also make sure the dashboard looks aesthetic. Make it feel aesthetic, modern, pull from design inspo from Campus Customs (HW 4 style), make it easy to follow / look at

**Result:**
- **Design source:** read the HW4 frontend for the Campus Customs style: navy `#00366b`, Nunito Sans and Open Sans, the serif "Y" mark, the announcement bar and the Collegiate Gothic skyline. `AGENTS.md` sets black-and-pink as the default style; the request for HW4 styling overrides it, as in HW4.
- **Built `frontend/`** (React + Vite + TypeScript):
  - Navy header with the checking-balance card (shows "−$X approved payment" after an approval) and Reset.
  - Ticket list with status pills and "to approve" counts.
  - Ticket header with a "Start agent team" button.
  - Five color-coded agent cards (working / done, latest action in plain English, tool chips, refusal count).
  - A live activity timeline.
  - A "What each agent did" summary from the Boss's delegation summaries, plus next steps and blockers.
  - An approval card with an "Approve as" name field.
  - A resolved banner and notifications when a run finishes.
  - A label on runs from before the last reset.
  - A layout that works on phones.
- **Backend changes:**
  - The audit trail now records each tool call and result live (the `activity` list), so the dashboard shows agents working mid-run instead of only after each finishes.
  - Events are sorted by real timestamps.
  - `/tickets` also returns sku, size, qty and notes.
- **Tested in the browser:**
  - Started ticket 102 from the dashboard and watched Facilities and Accounting work live.
  - Approved the $2,400 rent as "Test Human": checking went from $3,400 to $1,000 with the drop shown, and ticket 102 changed to ✓ Resolved.
  - Reset restored $3,400.
  - Fixed the header on a phone-sized screen (the Reset button was cut off).
  - `npm run build` passes.
- **Docs:** `frontend/README.md`, and a "Dashboard" section in `output/harness.md`.
- **Note:** a ticket only shows as resolved when it really is resolved, either by the Boss or after an approval like rent paid. Ticket 102 finished its run as `waiting_approval` and became resolved once the payment was approved.

### Prompt 2
> Let's get the front end to now talk to the backend at http://localhost:8000. On the backend allow the Vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. Start the board with this: npm run dev. This should open the React desk in my browser so I can pick tickets and watch agents. Write output/design.md with what I chose for the dashboard aesthetic specifications. Include that I chose these specifications because they make the dashboard more aesthetic, easy to follow / absorb, and easy to navigate.

**Result:**
- **Frontend → backend:** the backend address `http://localhost:8000` is now set explicitly in `frontend/.env` (`VITE_API_BASE`).
- **Allowed origins:** the backend's CORS setting was narrowed from "any origin" to exactly the Vite page (`http://localhost:5173`, `http://127.0.0.1:5173`), `GET`/`POST` only. Checked with curl: the Vite origin, including the POST pre-check, is allowed; other origins get no permission header.
- **Vite:** `vite.config.ts` now pins port 5173 (`strictPort`, so it stays on the allowed origin) and sets `open: true`, so `npm run dev` opens the desk in the browser.
- **Started:** restarted the backend, then started the board with `npm run dev`. The desk opened in the browser, and all 25 browser requests to the backend returned 200.
- **Design doc:** wrote `output/design.md` with the dashboard's design: brand and inspiration, color palette (including agent and status colors), typography, layout, components, motion, accessibility, and how it connects. Each choice is tagged with the user's reasons: more aesthetic 🎨, easy to follow and absorb 👁, easy to navigate 🧭.
- **Docs:** updated `output/harness.md` and `frontend/README.md`.

### Follow-up prompts
None.

---

## Problem 9 — Resolve the tickets

### Prompt 1
> Great, let's do Problem 9. That is titled Resolve the tickets. Before the testing the agents on a full run over the three tickets, let's reset the working database (data/campus_customs_new.db) again so we can start clean. let's make sure flag the current checking balance before doing that. Let's then run all three tickets on the board (101.102.103) until each is resolved. Open output/desk_tickets.html from Problem 6. On each ticket tab, fill the Actual section from this run: Which agents worked, what they delegated, which tools were used. Keep the Expected section - I will need it to compare for my reflection. On the cash tab of the same output/desk_tickets.html itemize the money to the following: starting checking balance (after reset), for EACH ticket how cahs changed when the ticket resolved, and why (which pay  / purchase/ dollar ammount), ending checking balance which must match cash_accounts in the working database. Please make sure all the math is correct. Also save output/resolved_tickets.json for each ticket, ID, final status, short outcome, what each agent contributed, and any human apporvals. output/resolved_board.html,this is a page that I should be able to double click with a scrneeshot of the React board for each resolved ticket (101, 102, 103). Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashbaord, and safety rules.

**Result:**
- **Balance before reset:** checking was $3,400.00, with all tickets open and nothing pending. Reset through `POST /reset`; checking after the reset was $3,400.00.
- **Prep before running:** ticket 103 had no way to be resolved, because price overrides need human approval and there was no tool for it.
  - Added the MCP tool `prepare_discount`, used by Accounting. It refuses prices below cost or not below list, and approving it moves no cash.
  - Added "when is a ticket resolved" rules to the Boss prompt.
  - Made the bill fields in `AccountingReport` optional.
  - Added discount support to the dashboard.
- **Runs**, through the same backend routes the board uses, with the board open in the browser:
  - **101**, 6 runs:
    1. Run 1: Accounting prepared the invoice 501 payment ($840) and a purchase order for 1 tee ($8). Both were approved, invoice first: checking $3,400 → $2,560 → $2,552.
    2. Run 2 failed: Portkey served a cached reply the Responses API rejected. Fixed with a cache force-refresh header.
    3. Run 3 failed: Accounting's report schema rejected an approved purchase order. Fixed by allowing that status, plus retries.
    4. Runs 4–5: the Boss kept the ticket in progress, waiting for a delivery. Also found that prompts were only loaded at startup, so they are now re-read every run.
    5. Run 6: the Boss resolved it (restock paid, customer draft with the 2026-09-05 arrival).
  - **102**, 1 run: Accounting prepared the $2,400 rent. Approved: checking $2,552 → $152, and the ticket resolved automatically.
  - **103**, 2 runs: 8 of 20 hoodies in stock. Accounting proposed $52 × 8 (10.3% off, $240 margin). Approved, with no cash moved. Run 2 resolved it. No restock was ordered: 12 × $22 = $264 is more than the $152 left.
  - Approvals were recorded as "N. Gupta (via Claude, at user's request)".
  - Total: 97 requests and 249,239 tokens.
- **Money check:** $3,400 − $840 − $8 − $2,400 − $0 = **$152.00**, which matches `cash_accounts`. The build script asserts this against the database.
- **`output/desk_tickets.html`:**
  - Each ticket's Actual section: agents involved, delegations by run, tools per agent, human approvals, and a short "Compared with Expected" note. The Expected sections were kept.
  - The Cash tab: balance before reset, starting balance, a ledger per ticket with subtotals, a math check, and the match with `cash_accounts`. The Reflection tab is still empty.
- **`output/resolved_tickets.json`:** per ticket, the ID, final status, short outcome, runs, each agent's contribution, human approvals and cash change.
- **`output/resolved_board.html`:** a page that opens with a double-click. It has a summary bar and, for each ticket, a card with outcome, contributions and approvals, plus a full-page screenshot of the React board. The screenshots were taken with Playwright using the installed Edge and are embedded as base64.
- **Dashboard change:** to make the screenshots honest, the board now shows every run on a ticket since the last reset (combined agent cards and summary, timeline split by run) instead of only the latest run. It can open a ticket with `?ticket=`.
- **`output/audit_trail.json`:** all 9 runs and 5 human actions (the reset and 4 approvals) were appended, 28 entries in total.
- **`output/harness.md`, finished:** run commands, the discount tool (14 tools in total), how the agents run, resolution rules, approval wording, measured usage, and a "Problem 9 results" section with the fixes and deliverables. `mcp_server/README.md` was updated to match; both were checked against the server's 14 tools.

### Follow-up prompts
None.

---

## Problem 10 — Reflection

### Prompt 1
> Let's move to Problem 10, titled Reflection. Let's open output/desk_tickets.html. We will now fill the reflection tab. Please include the following: Overall, the agent performed well. It is clear it was checking every step along the way, it even included tools when it realized one was missing to complete the task to resolve the ticket. The agent also clearly followed instruction to verify math is correct / flow of cash. I was surprised that there were many 'sub steps' missed in my expected reflection. The actual revealed that there is a larger web of approvals needed. For example, I didn't expect a need for Accounting to be involved in ticket 101 as part of invoice payments, I assumed tracking expected shipment from vendor was sufficient. One agent could have been simpler in that there wouldn't be as much necessary movement across all the different agents and tracking. Tools would allow a more consolidated action and possibly more efficiency in resolving open tickets. Campus customs could face issues with backorders / preorders, in which agents can track anticipated arrival and communication to customers for expected shipment given payment have already happened. They could also face issues with acquiring new locations' lease, so agents can support tracking how this impacts cash flow, as well as where cash is being redirected (i.e., to a new lease). Campus customs can also face navigation of returns and receiving back stock. Agents can support via tracking of influx of previously sold items and how this impacts financial statements via accounting. However, agents can't support everything. For example, agents can't support with memorizing customer profiles and supporting reorders per customer interest. This also extends to processing returns based on current capability. Agents cannot handle deal management of selling of property or equipment necessary at the store. Facilities seemed to be limited to rental-based and keeping business active.

**Result:** Filled the Reflection tab of `output/desk_tickets.html` with the user's reflection, in their words with light grammar edits. It's organized into five sections:
1. Overall performance
2. Expected vs. Actual
3. One agent vs. a team
4. Future issues where agents could help (backorders and preorders, a new location's lease, returns and stock coming back)
5. What the agents can't support

The ticket tabs (Expected and Actual) and the Cash tab were left unchanged, and no placeholders remain.

### Follow-up 1
> Yes

(Reply to the assistant's offer to reword the claim that "the agent" added a missing tool.)

**What was lacking:** Prompt 1 said "the agent … even included tools when it realized one was missing." In this project, the Campus Customs agent team didn't add tools. The coding assistant added `prepare_discount` when ticket 103 had no way to get a discount approved. Read as describing the agent team, the sentence was inaccurate.

**Result:** Reworded section 1 of the Reflection tab. It now refers to the agent team, says the missing-tool gap (approving ticket 103's discount) was found and `prepare_discount` was added, and gives the agents' own adaptation as the example: Accounting offered the discount only on the 8 hoodies in stock instead of ordering a restock the shop couldn't afford.

---

## Problem 11 — Submit to GitHub

### Prompt 1
> Okay let's wrap up with Problem 11 which is titled Submit to Github. Let's push the HW 5 cleanup folder/contents and push it to a public GitHub repository. Also put it in output/github_url.txt. Then, I need you to convey the 'repo URL'
> Do not put real.env into Github repo. Do include both the database files under data/ (original and working copy) so its easy for graders to run the app. README Should explain copy original DB to the working copy when I needed to clean a run, start an MCP server, start FastAPI backend, start the React board, reset the DB before a full three-ticket run.

**Result:**
- **Portability:** `.mcp.json` used absolute Windows paths. It now says `python mcp_server/server.py`, and `backend/llm.py:mcp_config()` resolves the interpreter and path at runtime. `requirements.txt` was trimmed to 5 pinned packages; the full freeze included Windows-only `pywin32`.
- **Secrets:**
  - Added `.gitignore`, which excludes every `.env`, `.venv/`, `node_modules/`, `frontend/dist/` and `.claude/`.
  - Added `.env.example` and `frontend/.env.example`.
  - A scan found the API key in no file.
- **Included:** both `data/campus_customs.db` (original) and `data/campus_customs_new.db` (working copy, in its final resolved state).
- **`README.md`:** setup, plus the five requested steps: (1) copy the original DB over the working copy for a clean run, (2) start the MCP server, (3) start the FastAPI backend, (4) start the React board, (5) reset the DB before a full three-ticket run. Also the routes, final results and safety rules.
- **Decisions asked of the user:** create the repo with GitHub CLI (it was already installed and logged in as `nguppy`); author commits with the GitHub noreply email; keep the approver name as recorded.
- **Repo:** created as public `nguppy/campus-customs-hw5` and pushed. The URL is saved in `output/github_url.txt`: https://github.com/nguppy/campus-customs-hw5

### Follow-up prompts
None yet.

---

<!--
Template for later problems:

## Problem N — <Title>

### Prompt 1
> <verbatim prompt>

**Result:** <what the assistant did>

### Follow-up 1
> <verbatim follow-up prompt>

**What was lacking:** <what the earlier prompt left out or got wrong, which made this follow-up necessary>

**Result:** <what changed>
-->
