interface ConfidenceRibbonPreviewProps {
  min: number
  p10: number
  mean: number
  p90: number
  max: number
  domainLo: number
  domainHi: number
  /** Top-ranked strategy — rendered in the purple accent; all others gray-blue. */
  fastest?: boolean
}

// STATIC preview of the signature Confidence Ribbon: a compressed distribution strip
// (whisker = min..max, box = p10..p90, tick = mean). Stage 6 fixes the color convention with
// hand-drawn SVG; the real data-driven D3 version is built in Stage 7. No D3 here by design.
export function ConfidenceRibbonPreview({
  min,
  p10,
  mean,
  p90,
  max,
  domainLo,
  domainHi,
  fastest = false,
}: ConfidenceRibbonPreviewProps) {
  const x = (v: number) => ((v - domainLo) / (domainHi - domainLo)) * 100
  const fill = fastest ? 'fill-fastest' : 'fill-ribbon-neutral'
  const stroke = fastest ? 'stroke-fastest' : 'stroke-ribbon-neutral'
  const mid = 12

  return (
    <svg viewBox="0 0 100 24" preserveAspectRatio="none" className="h-6 w-full">
      <line
        x1="0"
        y1={mid}
        x2="100"
        y2={mid}
        className="stroke-hairline"
        strokeWidth="1"
        vectorEffect="non-scaling-stroke"
      />
      <line
        x1={x(min)}
        y1={mid}
        x2={x(max)}
        y2={mid}
        className={stroke}
        strokeWidth="1"
        vectorEffect="non-scaling-stroke"
      />
      <rect
        x={x(p10)}
        y={mid - 5}
        width={x(p90) - x(p10)}
        height="10"
        className={fill}
        opacity="0.35"
      />
      <rect x={x(mean) - 0.4} y={mid - 7} width="0.8" height="14" className={fill} />
    </svg>
  )
}
