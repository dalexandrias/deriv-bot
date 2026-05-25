import { useCountdown } from '@/hooks/useCountdown'
import type { Signal } from '@/api/types'

interface Props {
  signal: Pick<Signal, 'entry_candle_time' | 'duration' | 'status'>
}

export function SignalCountdown({ signal }: Props) {
  const expiresAt =
    signal.entry_candle_time && signal.duration
      ? new Date(new Date(signal.entry_candle_time).getTime() + signal.duration * 1000)
      : null

  const countdown = useCountdown(expiresAt)

  if (signal.status !== 'pending') return <span className="text-lumen-faint">—</span>
  if (!expiresAt) return <span className="text-lumen-faint">—</span>
  if (!countdown) return <span className="text-lumen-muted text-xs italic">Aguardando...</span>

  return (
    <span className="font-mono tabular-nums text-xs text-lumen-primary">
      {countdown}
    </span>
  )
}
