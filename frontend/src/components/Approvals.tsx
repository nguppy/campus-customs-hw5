import { useState } from 'react'
import { formatMoney } from '../agents'
import type { BoardItem } from '../types'

interface Props {
  items: BoardItem[]
  busy: boolean
  onApprove: (item: BoardItem, name: string) => Promise<void>
}

const KIND_LABEL: Record<string, string> = { payment_request: 'Payment', purchase_order: 'Purchase order', discount_request: 'Discount' }

function amountOf(item: BoardItem): number | null {
  const d = item.details ?? {}
  const v = item.kind === 'purchase_order' ? d.total_cost : item.kind === 'discount_request' ? d.total_price : d.amount
  return typeof v === 'number' ? v : null
}

export default function Approvals({ items, busy, onApprove }: Props) {
  const [name, setName] = useState(() => localStorage.getItem('approver') ?? '')
  const [working, setWorking] = useState<number | null>(null)

  if (!items.length) return null

  const approve = async (item: BoardItem) => {
    localStorage.setItem('approver', name.trim())
    setWorking(item.id)
    try {
      await onApprove(item, name.trim())
    } finally {
      setWorking(null)
    }
  }

  return (
    <section className="card approvals" aria-label="Waiting for your approval">
      <div className="section-head">
        <h3>
          <span className="approval-icon" aria-hidden="true">!</span> Waiting for your approval
        </h3>
        <label className="approver">
          Approve as
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
        </label>
      </div>
      <ul className="approval-list">
        {items.map((item) => {
          const amount = amountOf(item)
          const d = item.details ?? {}
          return (
            <li key={item.id}>
              <span className="approval-kind">{KIND_LABEL[item.kind] ?? item.kind}</span>
              <span className="approval-body">
                <strong>{item.subject}</strong>
                <span className="muted small">
                  To {item.recipient} · prepared by {item.author}
                  {typeof d.balance_if_paid === 'number' && ` · checking after: ${formatMoney(d.balance_if_paid)}`}
                  {d.vendor_can_ship === false && ' · vendor blocked until its invoice is paid'}
                  {item.kind === 'discount_request' &&
                    ` · ${d.discount_pct}% off list · margin ${formatMoney(d.total_margin)} · no cash moves`}
                </span>
              </span>
              <span className="approval-amount">{amount !== null ? formatMoney(amount) : ''}</span>
              <button
                className="btn btn-primary btn-sm"
                disabled={busy || !name.trim() || working !== null}
                title={!name.trim() ? 'Enter your name first' : undefined}
                onClick={() => approve(item)}
              >
                {working === item.id ? 'Approving…' : 'Approve'}
              </button>
            </li>
          )
        })}
      </ul>
      <p className="muted small fine">Approving a payment or purchase order records your name in payments and lowers the checking balance. Approving a discount sets the price and moves no cash. Agents can't approve.</p>
    </section>
  )
}
