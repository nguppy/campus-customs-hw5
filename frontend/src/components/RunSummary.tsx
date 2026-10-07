import { AGENTS, STATUS_LABEL, summarizeReport, type AgentStatus } from '../agents'
import type { AgentRole, Ticket } from '../types'

interface Delegation {
  role: AgentRole
  task: string
  summary: string
}

/** Short summary of what each agent did on the ticket, across its runs since the last reset. */
export default function RunSummary({ statuses, ticket }: { statuses: Record<AgentRole, AgentStatus>; ticket: Ticket }) {
  const plan = statuses.boss.report
  if (!plan) return null
  const actions = (plan.recommended_actions as string[] | undefined) ?? []
  const blockers = (plan.blockers as string[] | undefined) ?? []
  const involved = AGENTS.filter((a) => statuses[a.role].state !== 'idle')

  return (
    <section className="card summary">
      <div className="section-head">
        <h3>What each agent did</h3>
        <span className={`pill pill-${ticket.status}`}>
          {ticket.state === 'resolved' && '✓ '}Ticket {STATUS_LABEL[ticket.status]}
        </span>
      </div>

      <ul className="summary-list">
        {involved.map((a) => {
          const s = statuses[a.role]
          // The Boss's most recent summary of this agent's work, from any run.
          const fromBoss = [...statuses.boss.reports]
            .reverse()
            .flatMap((r) => (r.delegations as Delegation[] | undefined) ?? [])
            .find((d) => d.role === a.role)?.summary
          const text = a.role === 'boss' ? String(plan.situation ?? '') : fromBoss || summarizeReport(a.role, s.report)
          return (
            <li key={a.role} className={`agent-${a.role}`}>
              <span className="avatar sm">{a.initials}</span>
              <span>
                <strong>{a.name}</strong>
                <span className="summary-text">{text}</span>
                {s.tools.length > 0 && <span className="summary-tools">Tools: {s.tools.join(', ')}</span>}
              </span>
            </li>
          )
        })}
      </ul>

      {(actions.length > 0 || blockers.length > 0) && (
        <div className="summary-cols">
          {actions.length > 0 && (
            <div>
              <h4>Boss's next steps</h4>
              <ol>{actions.map((a) => <li key={a}>{a}</li>)}</ol>
            </div>
          )}
          {blockers.length > 0 && (
            <div>
              <h4>Blockers</h4>
              <ul className="blockers">{blockers.map((b) => <li key={b}>{b}</li>)}</ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
