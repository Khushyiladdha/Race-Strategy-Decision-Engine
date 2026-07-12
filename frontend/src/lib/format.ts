// One home for number formatting so every figure on screen is consistent and monospace
// (build-plan §4, rule 5). Reused by Delta, Ticker, and the Stage 7 board/timeline.

/** 94.512 -> "1:34.512" */
export function formatLapTime(seconds: number): string {
  const sign = seconds < 0 ? '-' : ''
  const abs = Math.abs(seconds)
  const m = Math.floor(abs / 60)
  const s = abs - m * 60
  return `${sign}${m}:${s.toFixed(3).padStart(6, '0')}`
}

/** 94.512 -> "94.512s" */
export function formatSeconds(seconds: number, digits = 3): string {
  return `${seconds.toFixed(digits)}s`
}

/** +2.3 -> "+2.30", -0.85 -> "-0.85", 0 -> "±0.00" */
export function formatDelta(seconds: number, digits = 2): string {
  const v = Math.abs(seconds).toFixed(digits)
  if (seconds > 0) return `+${v}`
  if (seconds < 0) return `-${v}`
  return `±${v}`
}

/** 0.94 -> "94%" */
export function formatPct(fraction: number): string {
  return `${Math.round(fraction * 100)}%`
}

/** 5651.24 -> "1:34:11" (h:mm:ss) for total race times */
export function formatRaceTime(seconds: number): string {
  const total = Math.round(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}
