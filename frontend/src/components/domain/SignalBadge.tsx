import type { SignalDirection } from '@/api/types'

interface Props { direction: SignalDirection }

export function SignalBadge({ direction }: Props) {
  if (direction === 'CALL') {
    return (
      <span className="inline-block text-xs font-semibold font-body px-2.5 py-0.5 rounded-lumen-sm bg-lumen-up-soft text-lumen-up">
        COMPRA
      </span>
    )
  }
  return (
    <span className="inline-block text-xs font-semibold font-body px-2.5 py-0.5 rounded-lumen-sm bg-lumen-down-soft text-lumen-down">
      VENDA
    </span>
  )
}
