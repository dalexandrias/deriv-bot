import { useState, useEffect } from 'react'

export function useCountdown(expiresAt: Date | null): string {
  const [remaining, setRemaining] = useState<number>(() =>
    expiresAt ? Math.max(0, expiresAt.getTime() - Date.now()) : 0
  )

  useEffect(() => {
    if (!expiresAt) return
    const tick = () => setRemaining(Math.max(0, expiresAt.getTime() - Date.now()))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [expiresAt])

  if (!expiresAt || remaining <= 0) return ''
  const totalSecs = Math.ceil(remaining / 1000)
  const m = Math.floor(totalSecs / 60)
  const s = totalSecs % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
