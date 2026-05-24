import { BotStatusDot } from '@/components/domain/BotStatusDot'
import { useQuery } from '@tanstack/react-query'
import { botApi } from '@/api/endpoints/bot'
import { healthApi } from '@/api/endpoints/health'

export function Topbar() {
  const { data: status } = useQuery({
    queryKey: ['bot', 'status'],
    queryFn: botApi.getStatus,
    refetchInterval: 5000,
  })
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: 10000,
  })

  const dbOk = health?.db === 'ok'
  const wsOk = health?.deriv_ws === 'ok'

  return (
    <header className="h-16 flex-none border-b border-lumen-border bg-lumen-surface flex items-center justify-between px-6">
      <div />
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-xs text-lumen-muted">
          <span className={`w-1.5 h-1.5 rounded-full ${dbOk ? 'bg-lumen-live' : 'bg-lumen-error'}`} />
          DB
          <span className={`w-1.5 h-1.5 rounded-full ${wsOk ? 'bg-lumen-live' : 'bg-lumen-error'}`} />
          WS
        </div>
        <BotStatusDot status={status?.status ?? 'unknown'} />
      </div>
    </header>
  )
}
