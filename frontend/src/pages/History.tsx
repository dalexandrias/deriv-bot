import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { signalsApi } from '@/api/endpoints/signals'
import { SignalBadge } from '@/components/domain/SignalBadge'
import type { SignalOutcome, SignalDirection, SignalStatus } from '@/api/types'

type OutcomeFilter = 'ALL' | SignalOutcome
type DirectionFilter = 'ALL' | SignalDirection
type StatusFilter = 'ALL' | SignalStatus

export default function History() {
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>('ALL')
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>('ALL')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

  const { data: signals = [], isLoading } = useQuery({
    queryKey: ['signals', 'history', outcomeFilter, directionFilter],
    queryFn: () =>
      signalsApi.list({
        limit: 200,
        outcome: outcomeFilter !== 'ALL' ? outcomeFilter : undefined,
        direction: directionFilter !== 'ALL' ? directionFilter : undefined,
      }),
    refetchInterval: 15000,
  })

  const filtered = statusFilter === 'ALL'
    ? signals
    : signals.filter((s) => s.status === statusFilter)

  const btn = (active: boolean) =>
    `px-3 py-1.5 rounded-lumen-sm text-xs font-medium border transition-colors ` +
    (active
      ? 'bg-lumen-primary text-white border-lumen-primary'
      : 'bg-lumen-surface text-lumen-body border-lumen-border hover:bg-lumen-surface-2')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Histórico</h1>
        <p className="text-sm text-lumen-muted mt-1">
          Todos os sinais gerados.
          {signals.length > 0 && <span className="ml-1 font-mono">{filtered.length} de {signals.length}</span>}
        </p>
      </div>

      <div className="flex flex-wrap gap-4">
        <div className="flex gap-1.5 items-center">
          <span className="text-xs text-lumen-muted mr-1">Status:</span>
          {(['ALL', 'pending', 'resolved', 'aborted'] as StatusFilter[]).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)} className={btn(statusFilter === s)}>
              {s === 'ALL' ? 'Todos' : s === 'pending' ? 'Aguardando' : s === 'resolved' ? 'Resolvido' : 'Abortado'}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 items-center">
          <span className="text-xs text-lumen-muted mr-1">Resultado:</span>
          {(['ALL', 'WIN', 'LOSS'] as OutcomeFilter[]).map((o) => (
            <button key={o} onClick={() => setOutcomeFilter(o)} className={btn(outcomeFilter === o)}>
              {o === 'ALL' ? 'Todos' : o === 'WIN' ? 'Ganho' : 'Perda'}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 items-center">
          <span className="text-xs text-lumen-muted mr-1">Direção:</span>
          {(['ALL', 'CALL', 'PUT'] as DirectionFilter[]).map((d) => (
            <button key={d} onClick={() => setDirectionFilter(d)} className={btn(directionFilter === d)}>
              {d === 'ALL' ? 'Todos' : d === 'CALL' ? 'Compra' : 'Venda'}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-lumen-muted text-sm">Carregando...</div>
      ) : filtered.length === 0 ? (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-8 text-center space-y-1">
          <div className="text-lumen-muted text-sm">Nenhum sinal encontrado.</div>
          {signals.length === 0 && (
            <div className="text-xs text-lumen-faint">O bot ainda não gerou sinais. Aguarde o próximo ciclo de análise.</div>
          )}
        </div>
      ) : (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen overflow-hidden shadow-lumen">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-lumen-surface-2 border-b border-lumen-border">
                {['Hora', 'Ativo', 'TF', 'Sinal', 'Conf.', 'Status', 'Entrada', 'Saída', 'Resultado'].map((h) => (
                  <th key={h} className="text-left text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-3 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const isWin = s.outcome === 'WIN'
                const isLoss = s.outcome === 'LOSS'
                return (
                  <tr key={s.id} className="border-b border-lumen-border last:border-0 hover:bg-lumen-surface-2 transition-colors">
                    <td className="px-3 py-2.5 font-mono tabular-nums text-xs text-lumen-muted whitespace-nowrap">
                      {new Date(s.created_at).toLocaleString('pt-BR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-3 py-2.5 font-medium text-lumen-text">{s.symbol}</td>
                    <td className="px-3 py-2.5 text-lumen-muted">{s.timeframe}</td>
                    <td className="px-3 py-2.5"><SignalBadge direction={s.direction} /></td>
                    <td className="px-3 py-2.5 font-mono tabular-nums">{s.confidence.toFixed(2)}</td>
                    <td className="px-3 py-2.5">
                      {s.status === 'pending' && (
                        <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-lumen-sm bg-lumen-primary-soft text-lumen-primary">AGUARDANDO</span>
                      )}
                      {s.status === 'resolved' && !s.outcome && (
                        <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-lumen-sm bg-lumen-surface-2 text-lumen-muted">RESOLVIDO</span>
                      )}
                      {s.status === 'aborted' && (
                        <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-lumen-sm bg-lumen-surface-2 text-lumen-muted">ABORTADO</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-lumen-body">{s.entry_price ?? '—'}</td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-lumen-body">{s.exit_price ?? '—'}</td>
                    <td className="px-3 py-2.5">
                      {isWin && <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-lumen-sm bg-lumen-up-soft text-lumen-up">GANHO</span>}
                      {isLoss && <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-lumen-sm bg-lumen-down-soft text-lumen-down">PERDA</span>}
                      {!isWin && !isLoss && <span className="text-lumen-faint">—</span>}
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
