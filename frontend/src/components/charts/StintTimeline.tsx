import { scaleLinear } from 'd3-scale'

import type { Stint } from '../../lib/stints'
import { COMPOUND_STYLE } from '../../lib/tyres'

interface StintTimelineProps {
  stints: Stint[]
  totalLaps: number
  label?: string
  variant?: 'compact' | 'large'
}

const W = 600
const PAD = 8
const PIT_GAP = 5 // the visible gap between stints = the pit stop

const DIMS = {
  compact: { H: 52, barTop: 6, barH: 24, labelH: 0, letter: 12, axis: 9 },
  large: { H: 82, barTop: 26, barH: 38, labelH: 26, letter: 16, axis: 11 },
} as const

// D3 gantt of a strategy: one bar per stint, colored by compound, a gap marking each pit stop,
// and a lap axis. The large variant adds a compound + lap-count label above each stint and thicker
// bars, so the timeline can headline a screen. Uniform-scaling viewBox keeps text undistorted.
export function StintTimeline({
  stints,
  totalLaps,
  label,
  variant = 'compact',
}: StintTimelineProps) {
  const d = DIMS[variant]
  const x = scaleLinear()
    .domain([0, totalLaps])
    .range([PAD, W - PAD])

  const ticks: number[] = []
  for (let l = 0; l <= totalLaps; l += 10) ticks.push(l)
  if (ticks[ticks.length - 1] !== totalLaps) ticks.push(totalLaps)

  return (
    <div className="space-y-1">
      {label && (
        <span className="font-body text-[11px] uppercase tracking-wider text-muted">{label}</span>
      )}
      <svg viewBox={`0 0 ${W} ${d.H}`} className="w-full">
        {stints.map((s, i) => {
          const isLast = i === stints.length - 1
          const x0 = x(s.startLap - 1)
          const x1 = x(s.endLap) - (isLast ? 0 : PIT_GAP)
          const w = Math.max(0, x1 - x0)
          const style = COMPOUND_STYLE[s.compound]
          const laps = s.endLap - s.startLap + 1
          return (
            <g key={i}>
              {variant === 'large' && w > 24 && (
                <text
                  x={x0}
                  y={d.labelH - 8}
                  className="fill-muted font-body"
                  fontSize="10"
                  letterSpacing="0.05em"
                >
                  {s.compound} · {laps}L
                </text>
              )}
              <rect x={x0} y={d.barTop} width={w} height={d.barH} rx="3" className={style.fill} />
              {w > 12 && (
                <text
                  x={x0 + w / 2}
                  y={d.barTop + d.barH / 2}
                  dominantBaseline="central"
                  textAnchor="middle"
                  className="fill-ink-dark font-mono"
                  fontSize={d.letter}
                >
                  {style.letter}
                </text>
              )}
            </g>
          )
        })}
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={x(t)}
              y1={d.barTop + d.barH}
              x2={x(t)}
              y2={d.barTop + d.barH + 3}
              className="stroke-hairline"
              strokeWidth="1"
            />
            <text
              x={x(t)}
              y={d.H - 4}
              textAnchor="middle"
              className="fill-muted font-mono"
              fontSize={d.axis}
            >
              {t}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
