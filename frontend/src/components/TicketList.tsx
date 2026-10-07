import { STATUS_LABEL, TYPE_LABEL } from '../agents'
import type { Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  selected: number | null
  runningId: number | null
  pendingByTicket: Record<number, number>
  onSelect: (id: number) => void
}

const ICON: Record<string, string> = {
  customer_order: 'M6 7h12l-1 13H7L6 7zm3 0a3 3 0 0 1 6 0',
  rent_notice: 'M4 11l8-6 8 6v9h-5v-5h-6v5H4z',
  price_override: 'M4 12l8-8h7v7l-8 8-7-7zm11-5h.01',
}

export default function TicketList({ tickets, selected, runningId, pendingByTicket, onSelect }: Props) {
  return (
    <nav className="ticket-list" aria-label="Tickets">
      <div className="section-head">
        <h2>Tickets</h2>
        <span className="muted small">{tickets.filter((t) => t.state === 'open').length} open</span>
      </div>
      {tickets.map((t) => {
        const isResolved = t.state === 'resolved'
        return (
          <button
            key={t.id}
            className={`ticket-card ${selected === t.id ? 'selected' : ''} ${isResolved ? 'resolved' : ''}`}
            onClick={() => onSelect(t.id)}
            aria-current={selected === t.id}
          >
            <span className="ticket-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20">
                <path d={ICON[t.type] ?? ICON.customer_order} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
              </svg>
            </span>
            <span className="ticket-body">
              <span className="ticket-top">
                <span className="ticket-id">#{t.id}</span>
                <span className="ticket-type">{TYPE_LABEL[t.type] ?? t.type}</span>
              </span>
              <span className="ticket-subject">{t.subject}</span>
              <span className="ticket-requester">{t.requester}</span>
              <span className="ticket-tags">
                {runningId === t.id ? (
                  <span className="pill pill-running">
                    <span className="dot" /> Agents working
                  </span>
                ) : (
                  <span className={`pill pill-${t.status}`}>
                    {isResolved && '✓ '}
                    {STATUS_LABEL[t.status] ?? t.status}
                  </span>
                )}
                {pendingByTicket[t.id] ? <span className="pill pill-approval">{pendingByTicket[t.id]} to approve</span> : null}
              </span>
            </span>
          </button>
        )
      })}
    </nav>
  )
}
