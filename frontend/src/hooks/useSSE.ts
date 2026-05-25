import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useEventsStore } from '@/store/events'
import type { SSEEvent } from '@/api/types'

const SSE_URL = `${import.meta.env.VITE_API_URL ?? ''}/api/v1/events/stream`
const MAX_RETRY_MS = 30_000
const BASE_RETRY_MS = 1_000

export function useSSE() {
  const esRef = useRef<EventSource | null>(null)
  const retryMs = useRef(BASE_RETRY_MS)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const qc = useQueryClient()

  useEffect(() => {
    function connect() {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }

      const es = new EventSource(SSE_URL)
      esRef.current = es

      es.onopen = () => {
        retryMs.current = BASE_RETRY_MS
        useEventsStore.getState().setConnected(true)
      }

      es.onerror = () => {
        useEventsStore.getState().setConnected(false)
        es.close()
        esRef.current = null
        retryTimer.current = setTimeout(() => {
          retryMs.current = Math.min(retryMs.current * 2, MAX_RETRY_MS)
          connect()
        }, retryMs.current)
      }

      es.onmessage = (e) => {
        try {
          const event: SSEEvent = JSON.parse(e.data)
          const s = useEventsStore.getState()
          switch (event.type) {
            case 'status': {
              s.setBotStatus(event.data as any)
              qc.invalidateQueries({ queryKey: ['bot', 'status'] })
              break
            }
            case 'market':
              s.setMarket(event.data as any)
              break
            case 'signal_emitted': {
              const d = event.data as any
              s.upsertSignal(d)
              s.addLog({ message: `SINAL #${d.id} ${d.direction} conf=${Math.round((d.confidence ?? 0) * 100)}%`, level: 'info' })
              qc.invalidateQueries({ queryKey: ['signals'] })
              break
            }
            case 'signal_resolved': {
              const d = event.data as any
              s.upsertSignal(d)
              const lvl = d.outcome === 'WIN' ? 'info' : 'warning'
              const entryStr = d.entry_price != null ? Number(d.entry_price).toFixed(2) : '?'
              const exitStr = d.exit_price != null ? Number(d.exit_price).toFixed(2) : '?'
              s.addLog({ message: `RESULT #${d.id} ${(d.outcome ?? '?')} entrada=${entryStr} saída=${exitStr}`, level: lvl })
              qc.invalidateQueries({ queryKey: ['signals'] })
              qc.invalidateQueries({ queryKey: ['signals', 'stats'] })
              break
            }
            case 'llm_response': {
              const d = event.data as any
              s.addLog({ message: `LLM: ${d.direction ?? '?'} conf=${Math.round((d.confidence ?? 0) * 100)}%`, level: 'info' })
              break
            }
            case 'log':
            case 'error':
              s.addLog(event.data as any)
              break
          }
        } catch {
          // ignore parse errors
        }
      }
    }

    connect()

    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current)
      esRef.current?.close()
      esRef.current = null
    }
  }, [qc])
}
