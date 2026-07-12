import type { EvaluateResponse } from '../../lib/api'
import { OutcomeHistogram } from '../charts/OutcomeHistogram'
import { Panel } from '../ui/Panel'

// Overlays the finishing-time distributions of the top two shapes. Visual companion to win-probability:
// heavy overlap => no dominant strategy => low confidence.
export function OutcomeDistribution({ result }: { result: EvaluateResponse }) {
  const top = result.strategies.find((s) => s.key === result.robust_top_key) ?? result.strategies[0]
  const second = result.strategies.find((s) => s.key !== top.key)

  const series = [
    { counts: top.histogram, fastest: true, label: `${top.key} (best)` },
    ...(second ? [{ counts: second.histogram, fastest: false, label: `${second.key} (2nd)` }] : []),
  ]

  return (
    <Panel title="Outcome distribution">
      <OutcomeHistogram lo={result.histogram_lo} hi={result.histogram_hi} series={series} />
      <p className="mt-3 font-body text-xs text-muted">
        Monte Carlo finishing times for the top two shapes. When the distributions overlap, no
        single strategy dominates — which is what a low win probability means.
      </p>
    </Panel>
  )
}
