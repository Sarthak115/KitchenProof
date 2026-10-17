import { useTick } from '../lib/hooks'
import { mmss, secondsUntil } from '../lib/time'

export function Countdown({ until, warnAt = 60, className = '' }: { until?: string | null; warnAt?: number; className?: string }) {
  useTick(1000)
  const left = secondsUntil(until)
  const tone = left <= 0 ? 'text-red-700' : left <= warnAt ? 'text-amber-600' : ''
  return <span className={`font-mono tabular-nums ${tone} ${className}`}>{mmss(left)}</span>
}
