// Shapes returned by the FastAPI backend (backend/main.py).

export type TicketStatus = 'open' | 'in_progress' | 'waiting_approval' | 'blocked' | 'resolved'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: TicketStatus
  state: 'open' | 'resolved'
  sku: string | null
  size: string | null
  qty: number | null
  notes: string | null
  created_at: string
}

export type AgentRole = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export type EventType = 'started' | 'tool_call' | 'tool_result' | 'said' | 'report' | 'error' | 'human_action'

export interface AgentEvent {
  run_id: string
  tickets: number[] | null
  agent: AgentRole | 'human'
  delegated_by: AgentRole | null
  loop: number | null
  at: string
  type: EventType
  tool?: string
  args?: Record<string, unknown>
  result?: string
  text?: string | null
  report?: Record<string, unknown>
  action?: string
  board_id?: number
  approved_by?: string
}

export interface RunInfo {
  run_id: string
  ticket_id: number
  started_at: string
  finished_at?: string
  status?: 'completed' | 'error'
  error?: string
}

export interface EventsResponse {
  running: RunInfo | null
  last_run: RunInfo | null
  events: AgentEvent[]
}

export interface BoardItem {
  id: number
  ticket_id: number
  kind: 'customer_draft' | 'restock_request' | 'purchase_order' | 'payment_request' | 'discount_request'
  author: string
  recipient: string | null
  subject: string | null
  body: string | null
  details: Record<string, unknown> | null
  status: 'draft' | 'pending_approval' | 'approved'
  created_at: string
}

export interface Cash {
  account: string
  balance: number
  as_of: string
}

export interface ApproveResult {
  ok: boolean
  payment: { id: number; kind: string; amount: number; approved_by: string } | null
  new_balance?: number
  ticket?: Ticket
}
