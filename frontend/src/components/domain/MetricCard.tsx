interface Props {
  label: string
  value: string | number
  delta?: string
  deltaType?: 'up' | 'down' | 'neutral'
}

export function MetricCard({ label, value, delta, deltaType = 'neutral' }: Props) {
  const deltaColor =
    deltaType === 'up' ? 'text-lumen-up' :
    deltaType === 'down' ? 'text-lumen-down' :
    'text-lumen-muted'

  return (
    <div className="bg-lumen-surface-2 border border-lumen-border rounded-lumen p-4">
      <div className="text-[11px] tracking-[0.08em] uppercase text-lumen-muted font-medium">{label}</div>
      <div className="font-mono text-2xl font-semibold text-lumen-text mt-1.5 tabular-nums">{value}</div>
      {delta && (
        <div className={`font-mono text-[13px] mt-0.5 tabular-nums ${deltaColor}`}>{delta}</div>
      )}
    </div>
  )
}
