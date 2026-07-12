import type { EvaluateResponse } from '../../lib/api'
import { formatPct, formatRaceTime } from '../../lib/format'
import { stintsFromStrategy } from '../../lib/stints'
import type { Compound } from '../../lib/tyres'
import { StintTimeline } from '../charts/StintTimeline'
import { CircuitBlueprint } from '../layout/CircuitBlueprint'
import { TyreSequence } from '../ui/TyreChip'

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-chip border border-hairline bg-base/40 px-4 py-3">
      <div className="font-body text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-sm text-ink tabular-nums">{value}</div>
    </div>
  )
}

export function Hero({ result, metric }: { result: EvaluateResponse; metric: 'mean_s' | 'p90_s' }) {
  const top = result.strategies.find((s) => s.key === result.robust_top_key) ?? result.strategies[0]
  const stints = stintsFromStrategy(top.pit_laps, top.compounds, result.total_laps)

  return (
    <section className="relative overflow-hidden rounded-panel border border-hairline bg-panel shadow-raised">
      <CircuitBlueprint circuit={result.circuit_key} />
      {/* huge circuit-name watermark */}
      <span className="pointer-events-none absolute -bottom-6 right-2 select-none font-display text-[7rem] font-bold uppercase leading-none tracking-tighter text-ink/[0.04]">
        {result.circuit_key}
      </span>

      <div className="relative space-y-7 p-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="space-y-3">
            <div className="flex items-baseline gap-3">
              <span className="font-body text-xs uppercase tracking-[0.2em] text-muted">
                Recommended strategy
              </span>
              <span className="font-mono text-xs text-muted">{result.circuit_key}</span>
            </div>
            <TyreSequence compounds={top.compounds as Compound[]} size="lg" arrows />
          </div>

          <div className="flex gap-10">
            <div className="space-y-1">
              <div className="font-body text-[10px] uppercase tracking-wider text-muted">
                Expected finish
              </div>
              <div className="font-mono text-[2.6rem] leading-none text-ink tabular-nums">
                {formatRaceTime(top.distribution.mean_s)}
              </div>
            </div>
            <div className="relative space-y-1">
              {/* faint purple bloom behind the headline probability */}
              <div
                className="pointer-events-none absolute -inset-5 -z-0 opacity-[0.12] blur-2xl"
                style={{
                  background: 'radial-gradient(circle, var(--color-fastest), transparent 70%)',
                }}
              />
              <div className="relative font-body text-[10px] uppercase tracking-wider text-muted">
                Win probability
              </div>
              <div className="relative font-mono text-[2.6rem] leading-none text-fastest tabular-nums">
                {formatPct(top.win_probability)}
              </div>
              <div className="relative font-body text-[11px] text-muted">Model confidence</div>
            </div>
          </div>
        </div>

        <StintTimeline stints={stints} totalLaps={result.total_laps} variant="large" />

        <div className="grid grid-cols-2 gap-3 border-t border-hairline pt-5 sm:grid-cols-3 lg:grid-cols-5">
          <StatCard label="Laps" value={String(result.total_laps)} />
          <StatCard label="Stops" value={String(top.n_stops)} />
          <StatCard label="Safety car / lap" value={formatPct(result.sc_rate_per_lap)} />
          <StatCard label="Ranking" value={metric === 'mean_s' ? 'Mean' : 'P90'} />
          <StatCard label="Search space" value={result.n_strategies_generated.toLocaleString()} />
        </div>
      </div>
    </section>
  )
}
