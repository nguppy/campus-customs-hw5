import { formatMoney } from '../agents'
import type { Cash } from '../types'
import Skyline from './Skyline'

interface Props {
  cash: Cash | null
  drop: number | null // most recent decrease, shown briefly after an approval
  running: boolean
  onReset: () => void
}

export default function Header({ cash, drop, running, onReset }: Props) {
  return (
    <header className="hero">
      <div className="announcement">
        Desk date {cash?.as_of ?? '—'} · Agents run on gpt-6-luna · Drafts stay on the board, never sent · Cash
        moves only when a human approves
      </div>
      <div className="hero-inner">
        <div className="brand">
          <span className="brand-mark">Y</span>
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-sub">Agent Operations Desk</span>
          </span>
        </div>

        <div className="hero-right">
          <div className={`cash-card ${drop ? 'cash-dropped' : ''}`} aria-live="polite">
            <span className="cash-label">Checking balance</span>
            <span className="cash-amount">{cash ? formatMoney(cash.balance) : '—'}</span>
            {drop ? (
              <span className="cash-delta">−{formatMoney(drop)} approved payment</span>
            ) : (
              <span className="cash-note">as of {cash?.as_of ?? '—'} · no revenue modeled</span>
            )}
          </div>
          <button className="btn btn-outline-light" onClick={onReset} disabled={running} title="Restore the original database">
            Reset data
          </button>
        </div>
      </div>
      <Skyline />
    </header>
  )
}
