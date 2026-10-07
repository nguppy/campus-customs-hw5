# Campus Customs: Agent Dashboard (frontend)

React + Vite + TypeScript dashboard for the HW5 agent team. It calls the FastAPI backend from Problem 7.

## Run

1. Start the backend from `backend/`: `uvicorn main:app --reload --port 8000`
2. Start the dashboard from `frontend/`: `npm install` (first time only), then `npm run dev`
3. The desk opens at http://localhost:5173 (the backend allows this origin through CORS)

The backend address is set in `.env` (`VITE_API_BASE=http://localhost:8000`). Design choices are in `../output/design.md`.

## What it does

| Feature | Route used |
|---|---|
| Lists all tickets with their status (open, in progress, waiting approval, blocked, resolved) | `GET /tickets` |
| Pick a ticket and start the agent team | `POST /tickets/{id}/run` |
| Live view of each agent (working or done, its latest action, tools used) and an activity timeline | `GET /events` (polled every 1.5 s during a run) |
| Marks the ticket resolved when the run or approval finishes it: green banner, ✓ pill and a notification | `GET /tickets` |
| Short summary of what each agent did, plus the Boss's next steps and blockers | `GET /events` (agent reports) |
| Approve a prepared payment or purchase order (enter your name, click Approve) | `GET /approvals`, `POST /approvals/{id}/approve` |
| Checking balance in the header, which drops (with the amount shown) after an approved payment | `GET /cash` |
| Reset the data for a fresh run | `POST /reset` |

## Design

The styling follows the HW4 Campus Customs / Yale Bulldog Blue site:
- navy `#00366b` and white
- Nunito Sans headings and Open Sans body text
- the serif "Y" brand mark
- a navy announcement bar
- the Collegiate Gothic skyline in the header

Each agent has its own color, used on its card, avatar and timeline entries.
