import { useQuery } from '@tanstack/react-query'
import { signalsApi } from '@/api/endpoints/signals'
import { botApi } from '@/api/endpoints/bot'
import { MetricCard } from '@/components/domain/MetricCard'
import { BotStatusDot } from '@/components/domain/BotStatusDot'
import { useEventsStore } from '@/store/events'

export default function Overview() {
  const { data: stats } = useQuery({
    queryKey: ['signals', 'stats'],
    queryFn: signalsApi.getStats,
    refetchInterval: 10000,
  })
  const { data: botStatus } = useQuery({
    queryKey: ['bot', 'status'],
    queryFn: botApi.getStatus,
    refetchInterval: 5000,
  })
  const sseStatus = useEventsStore((s) => s.botStatus)
  const market = useEventsStore((s) => s.market)

  const derivedStatus = sseStatus?.status ?? (botStatus?.running ? 'running' : botStatus != null ? 'stopped' : 'unknown')
  const sseDetail = sseStatus?.detail

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display font-semibold text-lumen-text">Overview</h1>
          <p className="text-sm text-lumen-muted mt-1">Resumo geral do bot e performance.</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <BotStatusDot status={derivedStatus} />
          {sseDetail && <span className="text-xs text-lumen-muted">{sseDetail}</span>}
          {botStatus?.uptime != null && botStatus.uptime > 0 && (
            <span className="text-xs text-lumen-faint font-mono">
              uptime {Math.floor(botStatus.uptime / 60)}min
            </span>
          )}
        </div>
      </div>

      {stats?.total === 0 && botStatus?.last_cycle == null && botStatus?.running && (
        <div className="bg-lumen-primary-soft border border-lumen-primary-ring rounded-lumen px-4 py-3 text-sm text-lumen-primary">
          Bot rodando — aguardando primeiro ciclo de análise. O agente espera o fechamento do próximo candle de 5m antes de analisar.
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          label="Win rate"
          value={stats != null ? `${(stats.win_rate * 100).toFixed(1)}%` : '—'}
          deltaType="neutral"
        />
        <MetricCard
          label="Total de sinais"
          value={stats?.total ?? '—'}
          delta={stats ? `${stats.wins} vitórias · ${stats.losses} derrotas` : undefined}
          deltaType="neutral"
        />
        <MetricCard
          label="Conf. média"
          value={stats != null ? stats.avg_confidence.toFixed(2) : '—'}
          deltaType="neutral"
        />
      </div>

      {market && (
        <div className="grid grid-cols-2 gap-4">
          <MetricCard label="Última vela" value={market.last_candle_time || '—'} deltaType="neutral" />
          <MetricCard label="Próxima entrada" value={market.next_entry_time || '—'} deltaType="neutral" />
        </div>
      )}
    </div>
  )
}
