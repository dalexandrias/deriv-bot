import { api } from '../client'
import type { Candle } from '../types'

export const candlesApi = {
  list: (params?: { symbol?: string; timeframe?: string; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.symbol) q.set('symbol', params.symbol)
    if (params?.timeframe) q.set('timeframe', params.timeframe)
    if (params?.limit) q.set('limit', String(params.limit))
    return api.get<Candle[]>(`/candles/?${q}`)
  },
  symbols: () => api.get<string[]>('/candles/symbols'),
}
