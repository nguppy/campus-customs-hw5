import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { agentStatuses, formatMoney, latestRun, STATUS_LABEL, ticketRuns, TYPE_LABEL } from './agents'
import { api, API_BASE } from './api'
import ActivityFeed from './components/ActivityFeed'
import AgentBoard from './components/AgentBoard'
import Approvals from './components/Approvals'
import Header from './components/Header'
import RunSummary from './components/RunSummary'
import TicketList from './components/TicketList'
import type { AgentEvent, BoardItem, Cash, RunInfo, Ticket } from './types'

interface Toast {
  id: number
  tone: 'ok' | 'info' | 'error'
  text: string
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selected, setSelected] = useState<number | null>(
    () => Number((location.search + location.hash).match(/ticket=(d+)/)?.[1]) || null,
  )
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [running, setRunning] = useState<RunInfo | null>(null)
  const [approvals, setApprovals] = useState<BoardItem[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [drop, setDrop] = useState<number | null>(null)
  const [offline, setOffline] = useState(false)
  const [starting, setStarting] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const prevRunning = useRef<RunInfo | null>(null)

  const toast = useCallback((tone: Toast['tone'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, tone, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [t, ev, ap, c] = await Promise.all([api.tickets(), api.events(undefined, 400), api.approvals(), api.cash()])
      setTickets(t)
      setEvents(ev.events)
      setRunning(ev.running)
      setApprovals(ap)
      setCash(c)
      setOffline(false)
      setSelected((s) => s ?? t[0]?.id ?? null)

      // A run just finished: say how the ticket ended up.
      if (prevRunning.current && !ev.running) {
        const done = prevRunning.current
        const ticket = t.find((x) => x.id === done.ticket_id)
        if (ev.last_run?.status === 'error') toast('error', `Run on #${done.ticket_id} failed: ${ev.last_run.error}`)
        else if (ticket?.state === 'resolved') toast('ok', `Run finished: ticket #${done.ticket_id} is resolved ✓`)
        else if (ticket) toast('info', `Run finished: ticket #${done.ticket_id} is ${STATUS_LABEL[ticket.status].toLowerCase()}`)
      }
      prevRunning.current = ev.running
    } catch {
      setOffline(true)
    }
  }, [toast])

  // Poll fast while agents work, slowly otherwise.
  useEffect(() => {
    refresh()
    const id = setInterval(refresh, running ? 1500 : 10000)
    return () => clearInterval(id)
  }, [refresh, running])

  const ticket = tickets.find((t) => t.id === selected) ?? null
  // Show every run on this ticket since the last reset; with none, fall back to its latest (older) run.
  const lastReset = events.filter((e) => e.type === 'human_action' && e.action === 'reset').at(-1)?.at
  const run = useMemo(() => {
    if (!selected) return []
    const since = ticketRuns(events, selected, lastReset)
    return since.length ? since : latestRun(events, selected)
  }, [events, selected, lastReset])
  const runCount = new Set(run.map((e) => e.run_id)).size
  const statuses = useMemo(() => agentStatuses(run), [run])
  const isRunningHere = running?.ticket_id === selected
  // A run from before the latest reset no longer matches the database.
  const stale = !isRunningHere && run.length > 0 && !!lastReset && new Date(run[run.length - 1].at) < new Date(lastReset)
  const ticketApprovals = approvals.filter((a) => a.ticket_id === selected)
  const pendingByTicket = approvals.reduce<Record<number, number>>((m, a) => ({ ...m, [a.ticket_id]: (m[a.ticket_id] ?? 0) + 1 }), {})

  const startRun = async () => {
    if (!selected) return
    setStarting(true)
    try {
      await api.run(selected)
      toast('info', `Agent team started on ticket #${selected}`)
      await refresh()
    } catch (e) {
      toast('error', (e as Error).message)
    } finally {
      setStarting(false)
    }
  }

  const approve = async (item: BoardItem, name: string) => {
    try {
      const before = cash?.balance ?? null
      const res = await api.approve(item.id, name)
      if (res.payment && res.new_balance !== undefined) {
        if (before !== null) {
          setDrop(before - res.new_balance)
          setTimeout(() => setDrop(null), 8000)
        }
        toast('ok', `Approved by ${name}: paid ${formatMoney(res.payment.amount)}. Checking is now ${formatMoney(res.new_balance)}.`)
      } else {
        toast('ok', `Approved by ${name}: ${item.subject}. No cash moved.`)
      }
      await refresh()
    } catch (e) {
      toast('error', (e as Error).message)
    }
  }

  const reset = async () => {
    if (!confirm('Reset the database to its original values? Payments, drafts and ticket statuses will be cleared.')) return
    try {
      await api.reset()
      setDrop(null)
      toast('info', 'Database reset to the original values.')
      await refresh()
    } catch (e) {
      toast('error', (e as Error).message)
    }
  }

  return (
    <div className="app">
      <Header cash={cash} drop={drop} running={!!running} onReset={reset} />

      {offline && (
        <div className="offline">
          Can't reach the backend at <code>{API_BASE}</code>. Start it from <code>backend/</code> with{' '}
          <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="layout">
        <TicketList
          tickets={tickets}
          selected={selected}
          runningId={running?.ticket_id ?? null}
          pendingByTicket={pendingByTicket}
          onSelect={setSelected}
        />

        {ticket ? (
          <section className="detail">
            <div className="card ticket-head">
              <div>
                <span className="eyebrow">
                  #{ticket.id} · {TYPE_LABEL[ticket.type] ?? ticket.type}
                </span>
                <h1>{ticket.subject}</h1>
                <p className="muted">
                  {ticket.requester}
                  {ticket.sku && ` · ${ticket.qty} × ${ticket.sku} size ${ticket.size}`}
                </p>
              </div>
              <div className="ticket-actions">
                <span className={`pill pill-lg pill-${isRunningHere ? 'running' : ticket.status}`}>
                  {isRunningHere ? (
                    <>
                      <span className="dot" /> Agents working
                    </>
                  ) : (
                    <>
                      {ticket.state === 'resolved' && '✓ '}
                      {STATUS_LABEL[ticket.status]}
                    </>
                  )}
                </span>
                <button
                  className="btn btn-primary"
                  onClick={startRun}
                  disabled={!!running || starting || ticket.state === 'resolved'}
                  title={ticket.state === 'resolved' ? 'This ticket is resolved' : running ? 'Another run is in progress' : undefined}
                >
                  {isRunningHere ? 'Running…' : starting ? 'Starting…' : run.length ? 'Run team again' : 'Start agent team'}
                </button>
              </div>
            </div>

            {ticket.state === 'resolved' && (
              <div className="resolved-banner">
                <span className="check">✓</span> Ticket #{ticket.id} is resolved. Nothing left to do.
              </div>
            )}

            <Approvals items={ticketApprovals} busy={!!running} onApprove={approve} />

            <section className="card">
              <div className="section-head">
                <h3>The team</h3>
                <span className="muted small">
                  {isRunningHere
                    ? 'Live: updates as each agent works'
                    : stale
                      ? 'Previous run (before the last reset)'
                      : run.length
                        ? `${runCount} run${runCount === 1 ? '' : 's'} since the last reset`
                        : 'Idle'}
                </span>
              </div>
              <AgentBoard statuses={statuses} run={run} />
            </section>

            {stale && (
              <div className="stale-note">
                These results are from a run before the data was reset, so they may not match the current database. Start
                the team to get a fresh run.
              </div>
            )}

            {!isRunningHere && <RunSummary statuses={statuses} ticket={ticket} />}

            <section className="card">
              <div className="section-head">
                <h3>Activity</h3>
                <span className="muted small">What each agent said and which tools it used</span>
              </div>
              <ActivityFeed run={run} live={isRunningHere} />
            </section>
          </section>
        ) : (
          <section className="detail">
            <p className="empty">Loading tickets…</p>
          </section>
        )}
      </main>

      <footer className="footer">
        Campus Customs · 57 Broadway, New Haven · HW5 Multi-Agent Operations · Facts come from the campus-customs MCP server
      </footer>

      <div className="toasts" role="status">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`}>
            {t.text}
          </div>
        ))}
      </div>
    </div>
  )
}
