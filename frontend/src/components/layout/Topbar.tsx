import { BotStatusDot } from '@/components/domain/BotStatusDot'
import { useQuery } from '@tanstack/react-query'
import { healthApi } from '@/api/endpoints/health'
import { useEventsStore } from '@/store/events'
import { botApi } from '@/api/endpoints/bot'

export function Topbar() {
  const sseStatus = useEventsStore((s) => s.botStatus)
  const connected = useEventsStore((s) => s.connected)

  const { data: statusData } = useQuery({
    queryKey: ['bot', 'status'],
    queryFn: botApi.getStatus,
    refetchInterval: 5000,
  })

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: 15000,
  })

  // SSE status events carry { status: string } — prefer SSE, fall back to REST running boolean
  const botStatusStr = sseStatus?.status ?? (statusData?.running ? 'running' : statusData != null ? 'stopped' : 'unknown')
  const dbOk = health?.db === 'ok'
  const wsOk = health?.deriv_ws === 'ok'

  return (
    <header className="h-16 flex-none border-b border-lumen-border bg-lumen-surface flex items-center justify-between px-6">
      <div />
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3 text-xs text-lumen-muted">
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${dbOk ? 'bg-lumen-live' : 'bg-lumen-error'}`} />
            DB
          </span>
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${wsOk ? 'bg-lumen-live' : 'bg-lumen-error'}`} />
            WS
          </span>
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-lumen-live' : 'bg-lumen-paused'}`} />
            SSE
          </span>
        </div>
        <BotStatusDot status={botStatusStr} />
      </div>
    </header>
  )
}
