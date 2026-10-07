// Thin client for the Problem 7 backend routes.
import type { ApproveResult, BoardItem, Cash, EventsResponse, Ticket } from './types'

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail ?? `${res.status} ${res.statusText}`)
  return body as T
}

export const api = {
  tickets: () => request<Ticket[]>('/tickets'),
  run: (ticketId: number) => request<{ run_id: string }>(`/tickets/${ticketId}/run`, { method: 'POST' }),
  events: (ticketId?: number, limit = 300) =>
    request<EventsResponse>(`/events?limit=${limit}${ticketId ? `&ticket_id=${ticketId}` : ''}`),
  approvals: () => request<BoardItem[]>('/approvals'),
  approve: (boardId: number, approvedBy: string) =>
    request<ApproveResult>(`/approvals/${boardId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  cash: () => request<Cash>('/cash'),
  reset: () => request<{ reset: boolean }>('/reset', { method: 'POST' }),
}
