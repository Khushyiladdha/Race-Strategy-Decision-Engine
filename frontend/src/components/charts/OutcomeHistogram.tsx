import { scaleLinear } from 'd3-scale'

interface Series {
  counts: number[]
  fastest: boolean
  label: string
}

interface OutcomeHistogramProps {
  lo: number
  hi: number
  series: Series[] // usually two: top-1 (fastest) and top-2
}

const W = 600
const H = 150
const PAD_L = 8
const PAD_R = 8
const PAD_T = 8
const PAD_B = 22

// Overlaid outcome-distribution histogram: when the top strategies' bars sit on top of each other,
// low win-probability becomes visually obvious. Only the fastest series uses the purple accent.
export function OutcomeHistogram({ lo, hi, series }: OutcomeHistogramProps) {
  const bins = series[0]?.counts.length ?? 0
  const maxCount = Math.max(1, ...series.flatMap((s) => s.counts))

  const x = scaleLinear()
    .domain([0, bins])
    .range([PAD_L, W - PAD_R])
  const y = scaleLinear()
    .domain([0, maxCount])
    .range([H - PAD_B, PAD_T])
  const barW = (W - PAD_L - PAD_R) / bins

  const ticks = 5
  const labelFor = (t: number) => Math.round(lo + (t / ticks) * (hi - lo))

  return (
    <div className="space-y-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {series.map((s, si) => {
          const fill = s.fastest ? 'fill-fastest' : 'fill-ribbon-neutral'
          return (
            <g key={si} className={fill} opacity={s.fastest ? 0.55 : 0.4}>
              {s.counts.map((c, i) => (
                <rect
                  key={i}
                  x={x(i)}
                  y={y(c)}
                  width={Math.max(0, barW - 0.5)}
                  height={y(0) - y(c)}
                />
              ))}
            </g>
          )
        })}
        {/* x axis ticks in seconds */}
        {Array.from({ length: ticks + 1 }, (_, t) => (
          <text
            key={t}
            x={PAD_L + (t / ticks) * (W - PAD_L - PAD_R)}
            y={H - 6}
            textAnchor="middle"
            className="fill-muted font-mono"
            fontSize="9"
          >
            {labelFor(t)}s
          </text>
        ))}
      </svg>
      <div className="flex flex-wrap gap-4">
        {series.map((s, i) => (
          <span key={i} className="flex items-center gap-1.5">
            <span
              className={`inline-block h-2.5 w-2.5 rounded-sm ${
                s.fastest ? 'bg-fastest' : 'bg-ribbon-neutral'
              }`}
            />
            <span className="font-mono text-[11px] text-muted">{s.label}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
