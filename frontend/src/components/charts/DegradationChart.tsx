import { scaleLinear } from 'd3-scale'

import type { DegradationCurve } from '../../lib/api'
import { COMPOUND_STYLE, type Compound } from '../../lib/tyres'

const W = 620
const H = 300
const PAD_L = 44
const PAD_R = 16
const PAD_T = 16
const PAD_B = 34

// Fitted deg(n) = a·n + b·n² per compound, drawn as one line each. x = stint lap, y = lap-time loss
// vs a fresh tyre. Soft degrades fastest; this is the engine's model made legible.
export function DegradationChart({ compounds }: { compounds: DegradationCurve[] }) {
  const maxLap = Math.max(1, ...compounds.flatMap((c) => c.curve.map((p) => p.lap)))
  const maxLoss = Math.max(0.1, ...compounds.flatMap((c) => c.curve.map((p) => p.loss_s)))

  const x = scaleLinear()
    .domain([0, maxLap])
    .range([PAD_L, W - PAD_R])
  const y = scaleLinear()
    .domain([0, maxLoss])
    .range([H - PAD_B, PAD_T])

  const xTicks = Array.from({ length: Math.floor(maxLap / 5) + 1 }, (_, i) => i * 5)
  const yTicks = 4

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {/* y gridlines + labels */}
        {Array.from({ length: yTicks + 1 }, (_, i) => {
          const v = (i / yTicks) * maxLoss
          return (
            <g key={i}>
              <line
                x1={PAD_L}
                y1={y(v)}
                x2={W - PAD_R}
                y2={y(v)}
                className="stroke-hairline"
                strokeWidth="1"
              />
              <text
                x={PAD_L - 6}
                y={y(v) + 3}
                textAnchor="end"
                className="fill-muted font-mono"
                fontSize="9"
              >
                {v.toFixed(1)}s
              </text>
            </g>
          )
        })}
        {/* x ticks */}
        {xTicks.map((t) => (
          <text
            key={t}
            x={x(t)}
            y={H - 12}
            textAnchor="middle"
            className="fill-muted font-mono"
            fontSize="9"
          >
            {t}
          </text>
        ))}
        <text
          x={(PAD_L + W - PAD_R) / 2}
          y={H - 1}
          textAnchor="middle"
          className="fill-muted font-body"
          fontSize="9"
        >
          stint lap
        </text>

        {/* one line per compound */}
        {compounds.map((c) => {
          const stroke = COMPOUND_STYLE[c.compound as Compound]?.stroke
          const d = c.curve
            .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.lap)},${y(p.loss_s)}`)
            .join(' ')
          return <path key={c.compound} d={d} fill="none" className={stroke} strokeWidth="2" />
        })}
      </svg>

      <div className="flex flex-wrap gap-4">
        {compounds.map((c) => (
          <span key={c.compound} className="flex items-center gap-1.5">
            <span
              className={`inline-block h-2.5 w-4 rounded-sm ${COMPOUND_STYLE[c.compound as Compound]?.bg}`}
            />
            <span className="font-mono text-[11px] text-muted">
              {c.compound} · b={c.b.toFixed(4)}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}
