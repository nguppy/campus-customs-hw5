# Campus Customs Agent Desk: Dashboard Design

The design choices for the agent dashboard in `frontend/` (React + Vite + TypeScript).

**Why these specifications:** I chose them because they make the dashboard **more aesthetic**, **easy to follow and absorb**, and **easy to navigate**. Each choice below is tagged with the goal it serves:

| Tag | Goal |
|---|---|
| 🎨 | Aesthetic: polished, modern and on-brand for Campus Customs |
| 👁 | Easy to follow and absorb: you can tell at a glance what's happening and what it means |
| 🧭 | Easy to navigate: you always know where you are and what to do next |

---

## 1. Brand and inspiration
- **Source:** the Campus Customs / Yale Bulldog Blue style from the HW4 website, so the internal desk feels like part of the same brand. 🎨
- **Brand mark:** a white rounded tile with a serif **"Y"** (Georgia), next to "Campus Customs" / "AGENT OPERATIONS DESK". The same "Y" is the browser tab icon. 🎨 🧭
- **Navy announcement bar:** a thin bar across the top, as on the HW4 site, stating the desk's ground rules in one line: desk date, model, drafts never sent, cash moves only on human approval. 👁
- **Collegiate Gothic skyline:** a soft SVG silhouette of towers, spires, arches and elms along the bottom of the navy header, adapted from HW4. 🎨

## 2. Color palette
| Role | Color | Use |
|---|---|---|
| Primary navy | `#00366b` | Header, primary buttons, selected ticket, Boss agent |
| Navy dark | `#00264d` | Header gradient, hover states |
| Navy soft | `#e8eef6` | Background of the selected ticket card |
| Page background | `#f4f6f9` | Soft gray behind white cards |
| Cards | `#ffffff` with border `#e1e6ed` | All content panels |
| Text / muted text | `#1d1d1d` / `#5b6573` | Body text / secondary text |
| Accent coral | `#f04f36` | Errors, refusals, blockers (used sparingly) |

- **Navy and white as the base,** with one warm accent. This keeps the page calm and on-brand. 🎨
- **Color is saved for meaning:** coral only marks problems, amber only marks things waiting for you, and green only marks success. 👁

**Agent colors.** Each agent has its own color, used consistently on its card's top stripe, its avatar, its name in the timeline and its timeline dot. 👁 🧭

| Agent | Color |
|---|---|
| Boss | Navy `#00366b` |
| Inventory | Teal `#0f7470` |
| Accounting | Green `#1e7a4c` |
| Facilities | Amber-brown `#a8650a` |
| Customer Service | Plum `#6b4aa3` |

**Status colors** (pills):

| Status | Look |
|---|---|
| Open | Gray |
| In progress | Blue |
| Waiting approval | Amber |
| Blocked | Coral |
| Resolved | Green with a ✓ |
| Agents working | Solid navy with a blinking dot |

## 3. Typography
- **Headings:** Nunito Sans, extra-bold (800), the HW4 heading font. 🎨
- **Body:** Open Sans, at 15px with 1.55 line height for comfortable reading. 👁
- **Small uppercase labels** with wide letter-spacing ("CHECKING BALANCE", "#101 · CUSTOMER ORDER") mark what each block is without adding clutter. 👁
- **Numbers:** tabular figures, so money amounts line up and don't jump when they change. 👁
- **Tool names:** small monospace "chips" (e.g. `check_inventory`), so they read as technical labels apart from the plain-English text. 👁

## 4. Layout
- **Header:** brand on the left, and on the right the **checking balance card** (frosted glass on navy) and **Reset data**. The money is always visible. 🧭 👁
- **Two-column body:** a fixed-width **ticket list** on the left (320px, stays put while you scroll) and the **selected ticket's workspace** on the right. Picking a ticket never moves you off the page. 🧭
- **The workspace reads top to bottom in the order you need it:** 👁 🧭
  1. Ticket header: number, type, subject, requester, item, status, and the **Start agent team** button
  2. Resolved banner, when the ticket is done
  3. **Waiting for your approval** card, only when something needs you
  4. **The team:** five agent cards
  5. **What each agent did:** the summary after a run
  6. **Activity:** the full timeline
- **Overlap:** the content cards lift slightly over the bottom of the navy header, for a modern, layered look. 🎨
- **Phones:** on narrow screens the columns stack and the header wraps, so everything stays usable. 🧭

## 5. Components
- **Ticket cards:** an icon tile per ticket type (bag = order, house = rent, tag = price), the ticket number, type, subject, requester and a status pill. The selected ticket gets a navy edge and soft navy fill. A resolved ticket turns its icon and edge green. A "N to approve" pill shows where your attention is needed. 🧭 👁
- **Agent cards:** a colored avatar with initials (B, IN, AC, FA, CS), the agent's name, its state, its **latest action in plain English**, and the tools it used. 👁
  - **Working:** a pulsing ring, and the card lifts.
  - **Done:** green "Done".
  - **Not involved:** the card fades.
  - **Refused tool calls:** shown as a coral "N refused" chip.
- **Activity timeline:** a vertical line with a colored dot per step, a timestamp, the agent's name in its color, and a plain-English sentence such as "Delegated to Accounting", "Prepared a rent payment for human approval" or "Saved a draft message to Elm City Properties". Refusals are highlighted in coral. During a run it scrolls to the newest step. After a run it shows the last 12, with "Show all". 👁
- **Summary panel ("What each agent did"):** one line per agent, taken from the Boss's delegation summaries, with the tools used. Below that sit the Boss's **next steps** and **blockers** (coral bullets). 👁
- **Approval card:** a warm amber card that stands out from the rest of the page. It shows the item (Payment / Purchase order), what it's for, who it goes to, who prepared it, the checking balance after it's paid, and the amount in large type. You type your name once in "Approve as" (remembered for next time) and click **Approve**. 🧭 👁
- **Checking balance card:** a large amount. After an approval it briefly turns coral, pops, and shows "−$2,400.00 approved payment", so the drop is impossible to miss. 👁
- **Resolved banner:** a green bar with a check circle: "Ticket #102 is resolved. Nothing left to do." 👁
- **Older runs:** results from before the last reset are labeled "Previous run (before the last reset)", with a dashed note suggesting a fresh run. 👁
- **Notifications:** short pop-ups at the bottom right ("Agent team started on ticket #102", "Run finished: ticket #102 is resolved ✓", "Approved by …: paid $2,400.00…") that disappear after 6 seconds. Green means success, navy means information, coral means an error. 👁
- **Backend offline:** a clear coral banner with the exact command to start the backend. 🧭

## 6. Motion
- **Small and purposeful:** a pulse on working agents, a blinking dot on "Agents working", a pop on the cash card, notifications sliding in, and button press feedback. Motion only marks something changing. 🎨 👁
- **Reduced motion:** all animation turns off if the computer's "reduce motion" setting is on. 👁

## 7. Accessibility and clarity
- **Keyboard:** tickets and buttons are real buttons with visible focus outlines. 🧭
- **Screen readers:** the cash card and notifications announce changes.
- **Disabled buttons say why** in a tooltip, for example "Another run is in progress", "This ticket is resolved" or "Enter your name first". 🧭
- **Plain language everywhere:** tool calls are turned into sentences, so you don't have to read JSON to follow the agents. 👁

---

## How the dashboard connects
- **Frontend:** `frontend/` runs at **http://localhost:5173** (`npm run dev`, which opens the browser automatically).
- **Backend:** it calls the FastAPI backend at **http://localhost:8000**, set in `frontend/.env` (`VITE_API_BASE`).
- **Allowed origins:** the backend allows exactly the dashboard's origins (`http://localhost:5173`, `http://127.0.0.1:5173`), only for `GET`/`POST` with a `Content-Type` header. Any other website is blocked by the browser.
