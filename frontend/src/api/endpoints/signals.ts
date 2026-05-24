import { api } from '../client'
import type { Signal, SignalStats, SignalDirection, SignalOutcome } from '../types'

export const signalsApi = {
  list: (params?: { limit?: number; outcome?: SignalOutcome; direction?: SignalDirection }) => {
    const q = new URLSearchParams()
    if (params?.limit) q.set('limit', String(params.limit))
    if (params?.outcome) q.set('outcome', params.outcome)
    if (params?.direction) q.set('direction', params.direction)
    return api.get<Signal[]>(`/signals/?${q}`)
  },
  getStats: () => api.get<SignalStats>('/signals/stats'),
  get: (id: number) => api.get<Signal>(`/signals/${id}`),
}
