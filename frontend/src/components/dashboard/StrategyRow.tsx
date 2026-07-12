import type { StrategyOut } from '../../lib/api'
import { formatPct, formatRaceTime } from '../../lib/format'
import { stintsFromStrategy } from '../../lib/stints'
import type { Compound } from '../../lib/tyres'
import { ConfidenceRibbon } from '../charts/ConfidenceRibbon'
import { StintTimeline } from '../charts/StintTimeline'
import { Delta } from '../ui/Delta'
import { TyreSequence } from '../ui/TyreChip'

interface StrategyRowProps {
  strategy: StrategyOut
  rank: number
  topMean: number
  totalLaps: number
  domainLo: number
  domainHi: number
  fastest: boolean
  expanded: boolean
  onToggle: () => void
}

export function StrategyRow({
  strategy,
  rank,
  topMean,
  totalLaps,
  domainLo,
  domainHi,
  fastest,
  expanded,
  onToggle,
}: StrategyRowProps) {
  const d = strategy.distribution
  const stints = stintsFromStrategy(strategy.pit_laps, strategy.compounds, totalLaps)

  return (
    <div
      className={`border-b border-hairline transition-colors last:border-b-0 ${
        fastest ? 'relative border-l-2 border-l-fastest bg-fastest/[0.07] shadow-row-glow' : ''
      }`}
    >
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-surface-raised/40"
      >
        <span
          className={`flex h-6 w-7 shrink-0 items-center justify-center rounded-chip font-mono text-xs ${
            fastest ? 'text-fastest ring-1 ring-fastest/50' : 'text-muted'
          }`}
        >
          {rank}
        </span>
        <span className="w-24 shrink-0">
          <TyreSequence compounds={strategy.compounds as Compound[]} size="sm" />
        </span>
        <span className="w-28 shrink-0 font-mono text-xs text-muted">{strategy.key}</span>
        <span className="w-20 shrink-0 text-right font-mono text-sm text-ink tabular-nums">
          {formatRaceTime(d.mean_s)}
        </span>
        <span className="w-16 shrink-0 text-right">
          <Delta seconds={d.mean_s - topMean} />
        </span>
        <span
          className={`w-12 shrink-0 text-right font-mono text-sm tabular-nums ${
            fastest ? 'text-fastest' : 'text-ink'
          }`}
        >
          {formatPct(strategy.win_probability)}
        </span>
        <span className="min-w-0 flex-1">
          <ConfidenceRibbon
            best={d.best_s}
            p10={d.p10_s}
            mean={d.mean_s}
            p90={d.p90_s}
            worst={d.worst_s}
            domainLo={domainLo}
            domainHi={domainHi}
            fastest={fastest}
          />
        </span>
        <span className="w-4 shrink-0 font-mono text-xs text-muted">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <div className="animate-rise-in px-4 pb-5 pt-2">
          <StintTimeline
            stints={stints}
            totalLaps={totalLaps}
            variant="large"
            label="Stint timeline"
          />
        </div>
      )}
    </div>
  )
}
