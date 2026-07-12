import { formatDelta } from '../../lib/format'

interface DeltaProps {
  /** Seconds. By F1 convention negative = faster (gain); positive = slower (loss). */
  seconds: number
  /** Flip the meaning when a larger number is the good outcome. */
  invert?: boolean
  digits?: number
}

export function Delta({ seconds, invert = false, digits = 2 }: DeltaProps) {
  const isZero = seconds === 0
  const isGain = invert ? seconds > 0 : seconds < 0
  const color = isZero ? 'text-muted' : isGain ? 'text-gain' : 'text-loss'
  return <span className={`font-mono tabular-nums ${color}`}>{formatDelta(seconds, digits)}</span>
}
