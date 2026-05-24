import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { signalsApi } from '@/api/endpoints/signals'
import { SignalBadge } from '@/components/domain/SignalBadge'
import type { SignalOutcome, SignalDirection } from '@/api/types'

type OutcomeFilter = 'ALL' | SignalOutcome
type DirectionFilter = 'ALL' | SignalDirection

export default function History() {
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>('ALL')
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>('ALL')

  const { data: signals = [], isLoading } = useQuery({
    queryKey: ['signals', 'history', outcomeFilter, directionFilter],
    queryFn: () =>
      signalsApi.list({
        limit: 100,
        outcome: outcomeFilter !== 'ALL' ? outcomeFilter : undefined,
        direction: directionFilter !== 'ALL' ? directionFilter : undefined,
      }),
    refetchInterval: 30000,
  })

  const resolved = signals.filter((s) => s.status === 'resolved')

  const filterBtnClass = (active: boolean) =>
    `px-3 py-1.5 rounded-lumen-sm text-xs font-medium border transition-colors ` +
    (active
      ? 'bg-lumen-primary text-white border-lumen-primary'
      : 'bg-lumen-surface text-lumen-body border-lumen-border hover:bg-lumen-surface-2')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Histórico</h1>
        <p className="text-sm text-lumen-muted mt-1">Sinais resolvidos.</p>
      </div>

      {/* Filters */}
      <div className="flex gap-6">
        <div className="flex gap-1.5 items-center">
          <span className="text-xs text-lumen-muted mr-1">Resultado:</span>
          {(['ALL', 'WIN', 'LOSS'] as OutcomeFilter[]).map((o) => (
            <button key={o} onClick={() => setOutcomeFilter(o)} className={filterBtnClass(outcomeFilter === o)}>
              {o === 'ALL' ? 'Todos' : o === 'WIN' ? 'Ganho' : 'Perda'}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 items-center">
          <span className="text-xs text-lumen-muted mr-1">Direção:</span>
          {(['ALL', 'CALL', 'PUT'] as DirectionFilter[]).map((d) => (
            <button key={d} onClick={() => setDirectionFilter(d)} className={filterBtnClass(directionFilter === d)}>
              {d === 'ALL' ? 'Todos' : d === 'CALL' ? 'Compra' : 'Venda'}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-lumen-muted text-sm">Carregando...</div>
      ) : resolved.length === 0 ? (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-8 text-center text-lumen-muted text-sm">
          Nenhum sinal encontrado com esses filtros.
        </div>
      ) : (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen overflow-hidden shadow-lumen">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-lumen-surface-2 border-b border-lumen-border">
                {['Hora', 'Ativo', 'TF', 'Sinal', 'Conf.', 'Entrada', 'Saída', 'Resultado'].map((h) => (
                  <th key={h} className="text-left text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {resolved.map((s) => {
                const isWin = s.outcome === 'WIN'
                const isLoss = s.outcome === 'LOSS'
                return (
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
                    <td className="px-4 py-3 font-mono tabular-nums text-lumen-body">{s.entry_price ?? '—'}</td>
                    <td className="px-4 py-3 font-mono tabular-nums text-lumen-body">{s.exit_price ?? '—'}</td>
                    <td className="px-4 py-3">
                      {isWin && (
                        <span className="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-lumen-sm bg-lumen-up-soft text-lumen-up">GANHO</span>
                      )}
                      {isLoss && (
                        <span className="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-lumen-sm bg-lumen-down-soft text-lumen-down">PERDA</span>
                      )}
                      {!isWin && !isLoss && <span className="text-lumen-muted">—</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
