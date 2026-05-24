import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { candlesApi } from '@/api/endpoints/candles'

const LIMIT_OPTIONS = [50, 100, 200, 500]
const TIMEFRAME_OPTIONS = ['5m', '15m', '1m', '30m', '1h']

export default function Candles() {
  const [symbol, setSymbol] = useState('R_25')
  const [timeframe, setTimeframe] = useState('5m')
  const [limit, setLimit] = useState(100)

  const { data: symbols = [] } = useQuery({
    queryKey: ['candles', 'symbols'],
    queryFn: candlesApi.symbols,
    staleTime: 60000,
  })

  const { data: candles = [], isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['candles', symbol, timeframe, limit],
    queryFn: () => candlesApi.list({ symbol, timeframe, limit }),
    refetchInterval: 15000,
  })

  const selectClass =
    'px-3 py-1.5 text-sm border border-lumen-border rounded-lumen-sm bg-lumen-surface text-lumen-body focus:outline-none focus:ring-2 focus:ring-lumen-primary-ring focus:border-lumen-primary'

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display font-semibold text-lumen-text">Candles</h1>
          <p className="text-sm text-lumen-muted mt-1">
            {candles.length > 0
              ? `${candles.length} velas · atualizado às ${new Date(dataUpdatedAt).toLocaleTimeString('pt-BR')}`
              : 'Velas coletadas pelo collector.'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-lumen-muted">Ativo</label>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className={selectClass}>
            {symbols.length > 0
              ? symbols.map((s) => <option key={s} value={s}>{s}</option>)
              : <option value="R_25">R_25</option>}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-lumen-muted">Timeframe</label>
          <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className={selectClass}>
            {TIMEFRAME_OPTIONS.map((tf) => <option key={tf} value={tf}>{tf}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-lumen-muted">Quantidade</label>
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))} className={selectClass}>
            {LIMIT_OPTIONS.map((n) => <option key={n} value={n}>{n} velas</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="text-lumen-muted text-sm">Carregando...</div>
      ) : candles.length === 0 ? (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-8 text-center space-y-1">
          <div className="text-lumen-muted text-sm">Nenhuma vela encontrada para {symbol} {timeframe}.</div>
          <div className="text-xs text-lumen-faint">O collector precisa estar rodando para armazenar velas.</div>
        </div>
      ) : (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen overflow-hidden shadow-lumen">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-lumen-surface-2 border-b border-lumen-border">
                {['Horário', 'Dir.', 'Abertura', 'Máximo', 'Mínimo', 'Fechamento', 'Amplitude %'].map((h) => (
                  <th key={h} className="text-left text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...candles].reverse().map((c) => {
                const isUp = c.close >= c.open
                const amplitude = Math.abs((c.close - c.open) / c.open) * 100
                const dt = new Date(c.time * 1000)
                return (
                  <tr key={c.time} className="border-b border-lumen-border last:border-0 hover:bg-lumen-surface-2 transition-colors">
                    <td className="px-4 py-2.5 font-mono tabular-nums text-xs text-lumen-muted whitespace-nowrap">
                      {dt.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}{' '}
                      {dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-block w-2 h-2 rounded-sm ${isUp ? 'bg-lumen-up' : 'bg-lumen-down'}`} />
                    </td>
                    <td className="px-4 py-2.5 font-mono tabular-nums text-lumen-body">{c.open.toFixed(4)}</td>
                    <td className="px-4 py-2.5 font-mono tabular-nums text-lumen-up">{c.high.toFixed(4)}</td>
                    <td className="px-4 py-2.5 font-mono tabular-nums text-lumen-down">{c.low.toFixed(4)}</td>
                    <td className={`px-4 py-2.5 font-mono tabular-nums font-semibold ${isUp ? 'text-lumen-up' : 'text-lumen-down'}`}>
                      {c.close.toFixed(4)}
                    </td>
                    <td className={`px-4 py-2.5 font-mono tabular-nums text-xs ${isUp ? 'text-lumen-up' : 'text-lumen-down'}`}>
                      {isUp ? '+' : '-'}{amplitude.toFixed(3)}%
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
