import { AGENTS, describeToolCall, refusalReason, summarizeReport, type AgentStatus } from '../agents'
import type { AgentEvent, AgentRole } from '../types'

const STATE_LABEL = { idle: 'Not involved yet', working: 'Working…', done: 'Done', error: 'Error' }

function lastLine(s: AgentStatus, role: AgentRole): string {
  const e: AgentEvent | undefined = s.last
  if (!e) return ''
  switch (e.type) {
    case 'started':
      return e.delegated_by ? 'Picked up a task from the Boss' : 'Started on the ticket'
    case 'tool_call':
      return describeToolCall(e.tool ?? '', e.args)
    case 'report':
      return summarizeReport(role, e.report)
    case 'said':
      return e.text ?? ''
    case 'error':
      return e.text ?? 'Something went wrong'
    default:
      return ''
  }
}

export default function AgentBoard({ statuses, run }: { statuses: Record<AgentRole, AgentStatus>; run: AgentEvent[] }) {
  return (
    <div className="agent-grid">
      {AGENTS.map((a) => {
        const s = statuses[a.role]
        const refusals = run.filter((e) => e.agent === a.role && refusalReason(e.result)).length
        return (
          <article key={a.role} className={`agent-card agent-${a.role} state-${s.state}`}>
            <header className="agent-head">
              <span className="avatar" aria-hidden="true">
                {a.initials}
                {s.state === 'working' && <span className="pulse" />}
              </span>
              <span>
                <span className="agent-name">{a.name}</span>
                <span className={`agent-state state-${s.state}`}>{STATE_LABEL[s.state]}</span>
              </span>
            </header>
            <p className="agent-line">{lastLine(s, a.role) || <span className="muted">{a.blurb}</span>}</p>
            {(s.tools.length > 0 || refusals > 0) && (
              <footer className="agent-foot">
                {s.tools.slice(0, 4).map((t) => (
                  <span key={t} className="tool-chip">
                    {t}
                  </span>
                ))}
                {s.tools.length > 4 && <span className="tool-chip">+{s.tools.length - 4}</span>}
                {refusals > 0 && <span className="tool-chip chip-refused">{refusals} refused</span>}
              </footer>
            )}
          </article>
        )
      })}
    </div>
  )
}
