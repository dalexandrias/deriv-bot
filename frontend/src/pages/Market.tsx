import { useEventsStore } from '@/store/events'
import { useQuery } from '@tanstack/react-query'
import { botApi } from '@/api/endpoints/bot'

const INDICATOR_LABELS: Record<string, string> = {
  rsi: 'RSI',
  macd_line: 'MACD Line',
  macd_signal: 'MACD Signal',
  macd_histogram: 'MACD Hist.',
  adx: 'ADX',
  bb_position: 'BB Position',
  atr_pct: 'ATR %',
  price_vs_ema50: 'Price vs EMA50',
}

export default function Market() {
  const market = useEventsStore((s) => s.market)
  const sseStatus = useEventsStore((s) => s.botStatus)
  const { data: botStatus } = useQuery({
    queryKey: ['bot', 'status'],
    queryFn: botApi.getStatus,
    refetchInterval: 5000,
  })

  if (!market) {
    const isWaiting = sseStatus?.status === 'waiting' || (botStatus?.running && !botStatus.last_cycle)
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-lumen-text">Mercado</h1>
          <p className="text-sm text-lumen-muted mt-1">Indicadores em tempo real via SSE.</p>
        </div>
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-8 text-center space-y-2">
          <div className="text-lumen-muted text-sm">
            {isWaiting
              ? 'Bot aguardando fechamento do próximo candle de 5m...'
              : 'Aguardando primeiro evento de mercado via SSE.'}
          </div>
          {sseStatus?.detail && (
            <div className="text-xs text-lumen-faint font-mono">{sseStatus.detail}</div>
          )}
        </div>
      </div>
    )
  }

  const keys = Object.keys({ ...market.m5_indicators, ...market.m15_indicators })
  const uniqueKeys = [...new Set(keys)]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Mercado</h1>
        <p className="text-sm text-lumen-muted mt-1">
          Última vela: <span className="font-mono">{market.last_candle_time}</span>
          {' · '}
          Próxima entrada: <span className="font-mono">{market.next_entry_time}</span>
        </p>
      </div>

      {/* Indicator comparison table */}
      <div className="bg-lumen-surface border border-lumen-border rounded-lumen overflow-hidden shadow-lumen">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-lumen-surface-2 border-b border-lumen-border">
              <th className="text-left text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-4 py-3">Indicador</th>
              <th className="text-right text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-4 py-3">M5</th>
              <th className="text-right text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-4 py-3">M15</th>
            </tr>
          </thead>
          <tbody>
            {uniqueKeys.map((key) => {
              const m5 = market.m5_indicators[key]
              const m15 = market.m15_indicators[key]
              return (
                <tr key={key} className="border-b border-lumen-border last:border-0 hover:bg-lumen-surface-2 transition-colors">
                  <td className="px-4 py-3 text-lumen-body font-medium">{INDICATOR_LABELS[key] ?? key}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-lumen-body">
                    {m5 != null ? Number(m5).toFixed(4) : '—'}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-lumen-body">
                    {m15 != null ? Number(m15).toFixed(4) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pre-analysis flags */}
      {Object.keys(market.pre_analysis).length > 0 && (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-5 shadow-lumen">
          <h2 className="text-xs tracking-[0.08em] uppercase text-lumen-muted font-medium mb-4">Pré-análise</h2>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(market.pre_analysis).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-1.5">
                <span className="text-sm text-lumen-body capitalize">{k.replace(/_/g, ' ')}</span>
                <span className={`text-sm font-mono ${
                  v === true ? 'text-lumen-up' :
                  v === false ? 'text-lumen-down' :
                  'text-lumen-body'
                }`}>
                  {typeof v === 'boolean' ? (v ? 'Sim' : 'Não') : String(v)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
