import { useQuery } from '@tanstack/react-query'
import { signalsApi } from '@/api/endpoints/signals'
import { useEventsStore } from '@/store/events'
import { SignalBadge } from '@/components/domain/SignalBadge'
import { SignalCountdown } from '@/components/domain/SignalCountdown'
import type { Signal } from '@/api/types'

export default function Signals() {
  const { data: restSignals = [] } = useQuery({
    queryKey: ['signals', 'active'],
    queryFn: () => signalsApi.list({ limit: 50 }),
    refetchInterval: 10000,
  })
  const sseSignals = useEventsStore((s) => s.activeSignals)

  // merge: SSE updates override REST
  const merged = [...restSignals]
  for (const s of sseSignals) {
    const idx = merged.findIndex((x) => x.id === s.id)
    if (idx >= 0) merged[idx] = { ...merged[idx], ...s } as Signal
    else merged.unshift(s as unknown as Signal)
  }
  const pending = merged.filter((s) => s.status === 'pending')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Sinais Ativos</h1>
        <p className="text-sm text-lumen-muted mt-1">Sinais aguardando resolução.</p>
      </div>

      {pending.length === 0 ? (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-8 text-center text-lumen-muted text-sm">
          Nenhum sinal pendente.
        </div>
      ) : (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen overflow-hidden shadow-lumen">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-lumen-surface-2 border-b border-lumen-border">
                {['Hora', 'Ativo', 'TF', 'Sinal', 'Confiança', 'Falta', 'RSI', 'ADX', 'Score'].map((h) => (
                  <th key={h} className="text-left text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pending.map((s) => (
                <tr key={s.id} className="border-b border-lumen-border last:border-0 hover:bg-lumen-surface-2 transition-colors">
                  <td className="px-4 py-3 font-mono tabular-nums text-lumen-muted">
                    {new Date(s.created_at).toLocaleTimeString('pt-BR')}
                  </td>
                  <td className="px-4 py-3 font-medium text-lumen-text">{s.symbol}</td>
                  <td className="px-4 py-3 text-lumen-muted">{s.timeframe}</td>
                  <td className="px-4 py-3">
                    <SignalBadge direction={s.direction} />
                  </td>
                  <td className="px-4 py-3 font-mono tabular-nums">{s.confidence.toFixed(2)}</td>
                  <td className="px-4 py-3"><SignalCountdown signal={s} /></td>
                  <td className="px-4 py-3 font-mono tabular-nums text-lumen-body">{s.rsi?.toFixed(1) ?? '—'}</td>
                  <td className="px-4 py-3 font-mono tabular-nums text-lumen-body">{s.adx?.toFixed(1) ?? '—'}</td>
                  <td className="px-4 py-3 font-mono tabular-nums text-lumen-body">{s.confluence_score?.toFixed(2) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
