import { useState } from 'react'
import { extent } from 'd3-array'

import type { EvaluateResponse } from '../../lib/api'
import { Panel } from '../ui/Panel'
import { StrategyRow } from './StrategyRow'

export function StrategyBoard({ result }: { result: EvaluateResponse }) {
  const { strategies, robust_top_key, total_laps } = result
  const [expanded, setExpanded] = useState<string | null>(robust_top_key)

  // Shared domain so every ribbon is directly comparable (D3 for the math).
  const [lo, hi] = extent(
    strategies.flatMap((s) => [s.distribution.best_s, s.distribution.worst_s]),
  ) as [number, number]

  const topMean =
    strategies.find((s) => s.key === robust_top_key)?.distribution.mean_s ??
    strategies[0].distribution.mean_s

  return (
    <Panel title="Strategy Board">
      <div className="flex items-center gap-3 px-4 pb-2 font-body text-[10px] uppercase tracking-wider text-muted">
        <span className="w-7">#</span>
        <span className="w-24">Compounds</span>
        <span className="w-28">Key</span>
        <span className="w-20 text-right">Finish</span>
        <span className="w-16 text-right">Δ best</span>
        <span className="w-12 text-right">Win</span>
        <span className="min-w-0 flex-1">Confidence ribbon</span>
        <span className="w-4" />
      </div>
      <div className="-mx-5 -mb-5 border-t border-hairline">
        {strategies.map((s, i) => (
          <StrategyRow
            key={s.key}
            strategy={s}
            rank={i + 1}
            topMean={topMean}
            totalLaps={total_laps}
            domainLo={lo}
            domainHi={hi}
            fastest={s.key === robust_top_key}
            expanded={expanded === s.key}
            onToggle={() => setExpanded(expanded === s.key ? null : s.key)}
          />
        ))}
      </div>
    </Panel>
  )
}
