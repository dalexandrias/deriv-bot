interface Props { status: string }

export function BotStatusDot({ status }: Props) {
  const isLive = status === 'running' || status === 'analyzing' || status === 'connected'
  const isError = status === 'error' || status === 'disconnected'

  const dotClass = isError
    ? 'bg-lumen-error'
    : isLive
    ? 'bg-lumen-live'
    : 'bg-lumen-paused'

  const ringClass = isLive ? 'shadow-[0_0_0_3px_#DCFCE7]' : ''

  const label = isError ? 'Erro' : isLive ? 'Rodando' : status || 'Parado'

  return (
    <div className="flex items-center gap-2 text-sm text-lumen-body">
      <span className={`w-2 h-2 rounded-full flex-none ${dotClass} ${ringClass}`} />
      <span className="capitalize">{label}</span>
    </div>
  )
}
