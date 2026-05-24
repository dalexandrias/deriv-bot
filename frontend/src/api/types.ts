export type SignalDirection = 'CALL' | 'PUT'
export type SignalOutcome = 'WIN' | 'LOSS'
export type SignalStatus = 'pending' | 'resolved' | 'aborted'

export interface Signal {
  id: number
  symbol: string
  timeframe: string
  direction: SignalDirection
  confidence: number
  entry_price: number | null
  exit_price: number | null
  outcome: SignalOutcome | null
  status: SignalStatus
  duration: number | null
  rsi: number | null
  bb_position: number | null
  adx: number | null
  atr_pct: number | null
  price_vs_ema50: number | null
  macd_line: number | null
  macd_signal: number | null
  macd_histogram: number | null
  regime: string | null
  time_window: string | null
  m15_bias: string | null
  confluence_score: number | null
  strategy: string | null
  entry_candle_time: string | null
  created_at: string
  resolved_at: string | null
  reasoning: string | null
}

export interface SignalStats {
  total: number
  wins: number
  losses: number
  win_rate: number
  avg_confidence: number
}

export interface BotStatus {
  status: string
}

export interface BotConfig {
  [key: string]: string | number | boolean
}

export interface IndicatorConfig {
  id: number
  name: string
  indicator_type: string
  parameters: Record<string, number>
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface CollectorStatus {
  running: boolean
  symbols: string[]
  timeframes: string[]
}

export interface HealthStatus {
  db: 'ok' | 'error'
  deriv_ws: 'ok' | 'disconnected'
}

// SSE event types
export type SSEEventType = 'status' | 'market' | 'signal_emitted' | 'signal_resolved' | 'llm_response' | 'error' | 'log'

export interface SSEStatusPayload { status: string; detail: string }
export interface SSEMarketPayload {
  m5_indicators: Record<string, number>
  m15_indicators: Record<string, number>
  pre_analysis: Record<string, boolean | string>
  last_candle_time: string
  next_entry_time: string
}
export interface SSESignalPayload extends Partial<Signal> { id: number }
export interface SSEErrorPayload { message: string; detail?: string }
export interface SSELogPayload { message: string; level?: string }

export interface SSEEvent {
  type: SSEEventType
  data: SSEStatusPayload | SSEMarketPayload | SSESignalPayload | SSEErrorPayload | SSELogPayload
}
