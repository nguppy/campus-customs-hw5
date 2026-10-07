// Agent metadata + turning raw events into plain-English lines for the board.
import type { AgentEvent, AgentRole } from './types'

export interface AgentMeta {
  role: AgentRole
  name: string
  initials: string
  blurb: string
}

export const AGENTS: AgentMeta[] = [
  { role: 'boss', name: 'Boss', initials: 'B', blurb: 'Reads the ticket, delegates, makes the final call' },
  { role: 'inventory', name: 'Inventory', initials: 'IN', blurb: 'Stock by SKU and size, shortfalls, restock vendor' },
  { role: 'accounting', name: 'Accounting', initials: 'AC', blurb: 'Cash, invoices, margins; prepares payments' },
  { role: 'facilities', name: 'Facilities', initials: 'FA', blurb: 'The shop space: leases and rent' },
  { role: 'customer_service', name: 'Customer Service', initials: 'CS', blurb: 'Drafts messages for customers' },
]

export const agentName = (role: string) => AGENTS.find((a) => a.role === role)?.name ?? (role === 'human' ? 'You' : role)

const money = (n: unknown) =>
  typeof n === 'number' ? n.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) : String(n ?? '')

export const formatMoney = money

const DELEGATE: Record<string, string> = {
  ask_inventory: 'Inventory',
  ask_accounting: 'Accounting',
  ask_facilities: 'Facilities',
  ask_customer_service: 'Customer Service',
}

/** What a tool call means, in words. */
export function describeToolCall(tool: string, args: Record<string, unknown> = {}): string {
  if (DELEGATE[tool]) return `Delegated to ${DELEGATE[tool]}`
  switch (tool) {
    case 'get_ticket_details':
      return `Read ticket ${args.ticket_id ?? ''} and its linked records`
    case 'list_open_tickets':
      return 'Checked the open ticket queue'
    case 'check_inventory':
      return `Checked stock for ${args.sku}${args.size ? ` size ${args.size}` : ' (all sizes)'}`
    case 'list_vendors':
      return 'Looked up vendors, lead times and open invoices'
    case 'get_cash_position':
      return 'Checked cash and everything the shop owes'
    case 'list_board':
      return 'Reviewed drafts and pending items on the board'
    case 'update_ticket_status':
      return `Set the ticket to "${String(args.status ?? '').replace('_', ' ')}"`
    case 'save_draft':
      return `Saved a draft message to ${args.to}`
    case 'request_restock':
      return `Drafted a restock request: ${args.qty} × ${args.sku} ${args.size}`
    case 'prepare_purchase_order':
      return `Prepared a purchase order: ${args.qty} × ${args.sku} ${args.size}`
    case 'prepare_payment':
      return `Prepared a ${args.kind} payment for human approval`
    case 'prepare_discount':
      return `Proposed a discount: ${args.qty} at ${money(args.unit_price)} each, for human approval`
    default:
      return `Used ${tool}`
  }
}

/** Pull a refusal reason out of a tool result, if the MCP server refused. */
export function refusalReason(result?: string): string | null {
  if (!result || !result.includes('"refused": true')) return null
  const m = result.match(/"reason":\s*"([^"]+)"/)
  return m ? m[1] : 'Refused by the shop rules'
}

/** One-line summary of an agent's final typed report. */
export function summarizeReport(role: string, r: Record<string, unknown> = {}): string {
  switch (role) {
    case 'boss':
      return String(r.situation ?? '')
    case 'inventory': {
      const parts = [`${r.on_hand} on hand`, `shortfall ${r.shortfall}`]
      if (r.restock_vendor) parts.push(`restock via ${r.restock_vendor}${r.vendor_can_ship === false ? ' (blocked: open invoice)' : ''}`)
      return parts.join(' · ')
    }
    case 'accounting': {
      const parts = [String(r.item ?? '')]
      if (typeof r.amount_due === 'number') parts.push(money(r.amount_due))
      if (typeof r.balance_after_payment === 'number') parts.push(`checking ${money(r.cash_balance)} → ${money(r.balance_after_payment)}`)
      else parts.push(`checking ${money(r.cash_balance)}`)
      if (r.can_pay === false) parts.push('cannot pay')
      return parts.join(' · ')
    }
    case 'facilities':
      return `${r.space_name}: ${money(r.monthly_rent)} due ${r.next_due} (${r.days_until_due} days)`
    case 'customer_service':
      return `Draft to ${r.to}: "${r.subject}"`
    default:
      return ''
  }
}

/** Every agent-run event on a ticket after `since` (e.g. the last reset), oldest first. */
export function ticketRuns(events: AgentEvent[], ticketId: number, since?: string): AgentEvent[] {
  return events.filter(
    (e) => e.agent !== 'human' && e.tickets?.includes(ticketId) && (!since || new Date(e.at) >= new Date(since)),
  )
}

/** The events of the most recent agent run on a ticket. */
export function latestRun(events: AgentEvent[], ticketId: number): AgentEvent[] {
  const runs = events.filter((e) => e.agent !== 'human' && e.tickets?.includes(ticketId))
  if (!runs.length) return []
  const last = runs[runs.length - 1].run_id
  return runs.filter((e) => e.run_id === last)
}

export type AgentState = 'idle' | 'working' | 'done' | 'error'

export interface AgentStatus {
  state: AgentState
  last?: AgentEvent
  tools: string[]
  report?: Record<string, unknown> // latest report
  reports: Record<string, unknown>[] // every report, oldest first (one per run it worked in)
}

export function agentStatuses(run: AgentEvent[]): Record<AgentRole, AgentStatus> {
  const out = Object.fromEntries(AGENTS.map((a) => [a.role, { state: 'idle', tools: [], reports: [] }])) as unknown as Record<
    AgentRole,
    AgentStatus
  >
  for (const e of run) {
    if (e.agent === 'human') continue
    const s = out[e.agent]
    if (!s) continue
    if (e.type === 'started') s.state = 'working'
    if (e.type === 'tool_call' && e.tool && !s.tools.includes(e.tool)) s.tools.push(e.tool)
    if (e.type === 'report') {
      s.state = 'done'
      s.report = e.report
      if (e.report) s.reports.push(e.report)
    }
    if (e.type === 'error') s.state = 'error'
    if (e.type !== 'tool_result') s.last = e
  }
  return out
}

export const STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  in_progress: 'In progress',
  waiting_approval: 'Waiting approval',
  blocked: 'Blocked',
  resolved: 'Resolved',
}

export const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}
