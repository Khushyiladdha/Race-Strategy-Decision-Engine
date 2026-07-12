import { scaleLinear } from 'd3-scale'

interface ConfidenceRibbonProps {
  best: number
  p10: number
  mean: number
  p90: number
  worst: number
  /** Shared domain across all rows so ribbon widths are directly comparable. */
  domainLo: number
  domainHi: number
  fastest?: boolean
  size?: 'sm' | 'md'
}

// Data-driven signature ribbon: end-capped whisker (best..worst), rounded box (p10..p90), mean
// tick. The top-ranked strategy glows in the purple accent and wipes in on load; all others sit
// quiet in gray-blue. D3 supplies the scale; React renders the SVG.
export function ConfidenceRibbon({
  best,
  p10,
  mean,
  p90,
  worst,
  domainLo,
  domainHi,
  fastest = false,
  size = 'sm',
}: ConfidenceRibbonProps) {
  const x = scaleLinear().domain([domainLo, domainHi]).range([0, 100])
  const fill = fastest ? 'fill-fastest' : 'fill-ribbon-neutral'
  const stroke = fastest ? 'stroke-fastest' : 'stroke-ribbon-neutral'
  const mid = 12
  const glow = fastest ? 'drop-shadow-[0_0_4px_var(--color-fastest)] animate-ribbon-in' : ''
  const height = size === 'md' ? 'h-9' : 'h-6'

  return (
    <svg viewBox="0 0 100 24" preserveAspectRatio="none" className={`${height} w-full ${glow}`}>
      {/* whisker best..worst with rounded caps */}
      <line
        x1={x(best)}
        y1={mid}
        x2={x(worst)}
        y2={mid}
        className={stroke}
        strokeWidth="1.5"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
      {/* end caps */}
      {[best, worst].map((v, i) => (
        <line
          key={i}
          x1={x(v)}
          y1={mid - 3}
          x2={x(v)}
          y2={mid + 3}
          className={stroke}
          strokeWidth="1"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      ))}
      {/* interquartile box */}
      <rect
        x={x(p10)}
        y={mid - 5}
        width={Math.max(0, x(p90) - x(p10))}
        height="10"
        rx="1.5"
        className={fill}
        opacity="0.4"
      />
      {/* mean tick */}
      <rect x={x(mean) - 0.5} y={mid - 7} width="1" height="14" rx="0.5" className={fill} />
    </svg>
  )
}
