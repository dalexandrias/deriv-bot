import { useEventsStore } from '@/store/events'

const levelColor: Record<string, string> = {
  info:    'text-lumen-body',
  warning: 'text-lumen-paused',
  error:   'text-lumen-down',
  debug:   'text-lumen-muted',
}

export default function Logs() {
  const logs = useEventsStore((s) => s.logs)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Logs</h1>
        <p className="text-sm text-lumen-muted mt-1">
          {logs.length} entradas (últimas 500 via SSE)
        </p>
      </div>

      {logs.length === 0 ? (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-8 text-center text-lumen-muted text-sm">
          Nenhum log recebido ainda.
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
