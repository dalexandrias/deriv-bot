import { useQuery } from '@tanstack/react-query'
import { signalsApi } from '@/api/endpoints/signals'
import { MetricCard } from '@/components/domain/MetricCard'

export default function Stats() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['signals', 'stats'],
    queryFn: signalsApi.getStats,
    refetchInterval: 15000,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Estatísticas</h1>
        <p className="text-sm text-lumen-muted mt-1">Performance acumulada dos sinais.</p>
      </div>

      {isLoading ? (
        <div className="text-lumen-muted text-sm">Carregando...</div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          <MetricCard
            label="Win Rate"
            value={stats ? `${(stats.win_rate * 100).toFixed(1)}%` : '—'}
            deltaType={stats && stats.win_rate >= 0.55 ? 'up' : stats && stats.win_rate < 0.45 ? 'down' : 'neutral'}
          />
          <MetricCard
            label="Total de Sinais"
            value={stats?.total ?? '—'}
            deltaType="neutral"
          />
          <MetricCard
            label="Vitórias"
            value={stats?.wins ?? '—'}
            deltaType="neutral"
          />
          <MetricCard
            label="Derrotas"
            value={stats?.losses ?? '—'}
            deltaType="neutral"
          />
          <MetricCard
            label="Conf. Média"
            value={stats ? stats.avg_confidence.toFixed(3) : '—'}
            deltaType="neutral"
          />
          {stats && (
            <MetricCard
              label="Acertos Necessários"
              value="55.0%"
              delta="threshold de rentabilidade"
              deltaType="neutral"
            />
          )}
        </div>
      )}
    </div>
  )
}
