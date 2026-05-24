import { useEffect, useRef } from 'react'
import { useEventsStore } from '@/store/events'
import { useQuery } from '@tanstack/react-query'
import { signalsApi } from '@/api/endpoints/signals'

const levelColor: Record<string, string> = {
  info:    'text-lumen-body',
  warning: 'text-lumen-paused',
  error:   'text-lumen-down',
  debug:   'text-lumen-muted',
}

export default function Logs() {
  const logs = useEventsStore((s) => s.logs)
  const addLog = useEventsStore((s) => s.addLog)
  const seededRef = useRef(false)

  // Preload log entries from historical signals on first mount
  const { data: histSignals } = useQuery({
    queryKey: ['logs', 'seed'],
    queryFn: () => signalsApi.list({ limit: 100 }),
    staleTime: Infinity,
  })

  useEffect(() => {
    if (seededRef.current || !histSignals?.length) return
    seededRef.current = true
    // Add oldest-first so newest ends up at top of the ring buffer
    ;[...histSignals].reverse().forEach((s) => {
      if (s.status === 'resolved') {
        const lvl = s.outcome === 'WIN' ? 'info' : 'warning'
        const entryStr = s.entry_price != null ? Number(s.entry_price).toFixed(2) : '?'
        const exitStr  = s.exit_price  != null ? Number(s.exit_price).toFixed(2)  : '?'
        addLog({
          message: `[histórico] RESULT #${s.id} ${(s.outcome ?? '?').toUpperCase()} entrada=${entryStr} saída=${exitStr}`,
          level: lvl,
          timestamp: s.resolved_at ?? s.created_at,
        })
      }
      addLog({
        message: `[histórico] SINAL #${s.id} ${s.direction} conf=${Math.round((s.confidence ?? 0) * 100)}%`,
        level: 'info',
        timestamp: s.created_at,
      })
    })
  }, [histSignals, addLog])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Logs</h1>
        <p className="text-sm text-lumen-muted mt-1">
          {logs.length} entradas (últimas 500 · SSE ao vivo + histórico)
        </p>
      </div>

      {logs.length === 0 ? (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-8 text-center space-y-2">
          <p className="text-lumen-muted text-sm">Nenhum log ainda.</p>
          <p className="text-lumen-faint text-xs">
            Os logs aparecem aqui quando o bot emite sinais, recebe respostas do LLM ou encontra erros.
          </p>
        </div>
      ) : (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen overflow-hidden shadow-lumen">
          <div className="divide-y divide-lumen-border max-h-[70vh] overflow-y-auto">
            {logs.map((log) => (
              <div key={log.id} className="flex gap-4 px-4 py-2.5 hover:bg-lumen-surface-2 transition-colors">
                <span className="font-mono tabular-nums text-xs text-lumen-muted flex-none w-20">
                  {new Date(log.timestamp).toLocaleTimeString('pt-BR')}
                </span>
                <span className={`text-xs font-mono uppercase flex-none w-16 ${levelColor[log.level] ?? 'text-lumen-body'}`}>
                  {log.level}
                </span>
                <span className="text-sm text-lumen-body break-all">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
