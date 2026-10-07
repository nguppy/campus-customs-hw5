import { Fragment, useEffect, useRef, useState } from 'react'
import { agentName, describeToolCall, refusalReason, summarizeReport } from '../agents'
import type { AgentEvent } from '../types'

function line(e: AgentEvent): { text: string; detail?: string; tone?: string } | null {
  switch (e.type) {
    case 'started':
      return e.delegated_by
        ? { text: `picked up a task from ${agentName(e.delegated_by)}`, detail: e.text ?? undefined }
        : { text: 'started working the ticket' }
    case 'tool_call':
      return { text: describeToolCall(e.tool ?? '', e.args), tone: e.tool?.startsWith('ask_') ? 'delegate' : 'tool' }
    case 'tool_result': {
      const reason = refusalReason(e.result)
      return reason ? { text: `${e.tool} was refused`, detail: reason, tone: 'refused' } : null
    }
    case 'said':
      return { text: 'said', detail: e.text ?? undefined }
    case 'report':
      return { text: 'reported back', detail: summarizeReport(e.agent, e.report), tone: 'report' }
    case 'error':
      return { text: 'hit an error', detail: e.text ?? undefined, tone: 'refused' }
    default:
      return null
  }
}

const time = (at: string) => new Date(at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })

export default function ActivityFeed({ run, live }: { run: AgentEvent[]; live: boolean }) {
  const [showAll, setShowAll] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  const runOrder = [...new Set(run.map((e) => e.run_id))]
  const rows = run.map((e) => ({ e, l: line(e) })).filter((r) => r.l)
  const visible = showAll || live ? rows : rows.slice(-12)

  useEffect(() => {
    if (live) end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [rows.length, live])

  if (!rows.length) return <p className="empty">No agent activity yet. Start the team to watch them work.</p>

  return (
    <div className="feed">
      {!showAll && !live && rows.length > visible.length && (
        <button className="link-btn" onClick={() => setShowAll(true)}>
          Show all {rows.length} steps
        </button>
      )}
      <ol>
        {visible.map(({ e, l }, i) => (
          <Fragment key={`${e.at}-${i}`}>
          {runOrder.length > 1 && (i === 0 || visible[i - 1].e.run_id !== e.run_id) && (
            <li className="feed-run">
              Run {runOrder.indexOf(e.run_id) + 1} of {runOrder.length}
            </li>
          )}
          <li className={`feed-row agent-${e.agent} tone-${l!.tone ?? 'plain'}`}>
            <span className="feed-dot" aria-hidden="true" />
            <span className="feed-time">{time(e.at)}</span>
            <span className="feed-main">
              <strong>{agentName(e.agent)}</strong> {l!.text}
              {l!.detail && <span className="feed-detail">{l!.detail}</span>}
            </span>
          </li>
          </Fragment>
        ))}
      </ol>
      <div ref={end} />
    </div>
  )
}
