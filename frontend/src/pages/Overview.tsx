import { useQuery } from '@tanstack/react-query'
import { signalsApi } from '@/api/endpoints/signals'
import { MetricCard } from '@/components/domain/MetricCard'
import { useEventsStore } from '@/store/events'

export default function Overview() {
  const { data: stats } = useQuery({
    queryKey: ['signals', 'stats'],
    queryFn: signalsApi.getStats,
    refetchInterval: 15000,
  })
  const market = useEventsStore((s) => s.market)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Overview</h1>
        <p className="text-sm text-lumen-muted mt-1">Resumo geral do bot e performance.</p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          label="Win rate"
          value={stats ? `${(stats.win_rate * 100).toFixed(1)}%` : '—'}
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
          value={stats ? stats.avg_confidence.toFixed(2) : '—'}
          deltaType="neutral"
        />
      </div>
      {market && (
        <div className="grid grid-cols-2 gap-4">
          <MetricCard
            label="Última vela"
            value={market.last_candle_time ?? '—'}
            deltaType="neutral"
          />
          <MetricCard
            label="Próxima entrada"
            value={market.next_entry_time ?? '—'}
            deltaType="neutral"
          />
        </div>
      )}
    </div>
  )
}
