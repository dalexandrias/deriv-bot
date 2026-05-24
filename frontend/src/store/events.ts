import { create } from 'zustand'
import type {
  SSEStatusPayload,
  SSEMarketPayload,
  SSESignalPayload,
  SSEErrorPayload,
  SSELogPayload,
} from '@/api/types'

interface LogEntry {
  id: number
  message: string
  level: string
  timestamp: string
}

interface EventsState {
  botStatus: SSEStatusPayload | null
  market: SSEMarketPayload | null
  activeSignals: SSESignalPayload[]
  logs: LogEntry[]
  connected: boolean
  setBotStatus: (p: SSEStatusPayload) => void
  setMarket: (p: SSEMarketPayload) => void
  upsertSignal: (p: SSESignalPayload) => void
  addLog: (p: SSEErrorPayload | SSELogPayload) => void
  setConnected: (v: boolean) => void
}

let logId = 0

export const useEventsStore = create<EventsState>((set) => ({
  botStatus: null,
  market: null,
  activeSignals: [],
  logs: [],
  connected: false,
  setBotStatus: (p) => set({ botStatus: p }),
  setMarket: (p) => set({ market: p }),
  upsertSignal: (p) =>
    set((s) => {
      const idx = s.activeSignals.findIndex((x) => x.id === p.id)
      if (idx >= 0) {
        const updated = [...s.activeSignals]
        updated[idx] = { ...updated[idx], ...p }
        return { activeSignals: updated }
      }
      return { activeSignals: [p, ...s.activeSignals] }
    }),
  addLog: (p) =>
    set((s) => ({
      logs: [
        {
          id: logId++,
          message: (p as SSELogPayload).message ?? (p as SSEErrorPayload).message,
          level: (p as SSELogPayload).level ?? 'error',
          timestamp: new Date().toISOString(),
        },
        ...s.logs.slice(0, 499), // ring buffer of 500
      ],
    })),
  setConnected: (v) => set({ connected: v }),
}))
