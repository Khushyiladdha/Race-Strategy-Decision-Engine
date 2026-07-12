import { useEffect, useState } from 'react'

import { getRaces, getValidation, type ValidationDetailOut } from '../lib/api'
import { formatSeconds } from '../lib/format'
import { useAsync } from '../lib/hooks'
import { stintsFromStrategy } from '../lib/stints'
import { CircuitPicker } from '../components/validation/CircuitPicker'
import { StintTimeline } from '../components/charts/StintTimeline'
import { Delta } from '../components/ui/Delta'
import { Panel } from '../components/ui/Panel'
import { ErrorNote, Loading } from '../components/ui/Status'

function Metric({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  const tone = ok === undefined ? 'text-ink' : ok ? 'text-gain' : 'text-loss'
  return (
    <div className="space-y-1">
      <div className="font-body text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`font-mono text-sm ${tone}`}>{value}</div>
    </div>
  )
}

function ValidationDetail({ v }: { v: ValidationDetailOut }) {
  const engine = stintsFromStrategy(v.predicted_pit_laps, v.predicted_compounds, v.total_laps)
  const actual = stintsFromStrategy(v.actual.pit_laps, v.actual.compounds, v.total_laps)

  return (
    <div className="animate-rise-in space-y-8">
      <Panel title={`${v.circuit_key} — engine vs. ${v.actual.winner}`}>
        <div className="relative space-y-6">
          <StintTimeline
            stints={engine}
            totalLaps={v.total_laps}
            label="Engine recommendation"
            variant="large"
          />
          <div className="flex items-center gap-3" aria-hidden="true">
            <div className="h-px flex-1 bg-hairline" />
            <span className="rounded-full border border-hairline bg-surface-raised px-3 py-0.5 font-display text-xs font-semibold text-muted">
              VS
            </span>
            <div className="h-px flex-1 bg-hairline" />
          </div>
          <StintTimeline
            stints={actual}
            totalLaps={v.total_laps}
            label={`Actual winner — ${v.actual.winner}`}
            variant="large"
          />
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Panel title="Comparison metrics">
          <div className="grid grid-cols-2 gap-4">
            <Metric
              label="Stop count"
              value={v.metrics.stop_count_match ? 'match' : 'differ'}
              ok={v.metrics.stop_count_match}
            />
            <Metric
              label="Pit-lap MAE"
              value={v.metrics.pit_lap_mae === null ? 'N/A' : `${v.metrics.pit_lap_mae} laps`}
            />
            <Metric label="First-stop error" value={`${v.metrics.first_stop_abs_error} laps`} />
            <Metric
              label="Compound match"
              value={v.metrics.compound_match}
              ok={v.metrics.compound_match === 'exact'}
            />
          </div>
        </Panel>

        <Panel title="Timing axis (free-air)">
          <div className="grid grid-cols-2 gap-4">
            <Metric label="Predicted" value={formatSeconds(v.timing.predicted_total_s, 0)} />
            <Metric label="Actual est." value={formatSeconds(v.timing.actual_total_est_s, 0)} />
            <div className="space-y-1">
              <div className="font-body text-[11px] uppercase tracking-wider text-muted">Error</div>
              <div className="font-mono text-sm">
                <Delta seconds={v.timing.time_error_s} />
              </div>
            </div>
            <Metric label="Lap coverage" value={`${Math.round(v.timing.lap_coverage * 100)}%`} />
          </div>
        </Panel>
      </div>

      <Panel title="Why they disagree">
        <div className="space-y-3">
          <p className="font-body text-sm text-ink">{v.explanation}</p>
          {v.flags.length > 0 && (
            <ul className="space-y-1">
              {v.flags.map((f, i) => (
                <li key={i} className="font-mono text-xs text-muted">
                  • {f}
                </li>
              ))}
            </ul>
          )}
          <p className="font-body text-[11px] text-muted">
            The engine optimizes free-air pace; it ignores track position, traffic and the undercut
            — so an earlier real stop is expected where those forces dominate.
          </p>
        </div>
      </Panel>
    </div>
  )
}

export function ValidationView() {
  const races = useAsync(getRaces, [])
  const [selected, setSelected] = useState<string>('')

  useEffect(() => {
    if (!selected && races.data) {
      const first = races.data.find((r) => r.can_generate)
      if (first) setSelected(first.circuit_key)
    }
  }, [races.data, selected])

  const validation = useAsync<ValidationDetailOut | null>(
    () => (selected ? getValidation(selected) : Promise.resolve(null)),
    [selected],
  )

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h1 className="font-display text-xl font-semibold text-ink">Historical validation</h1>
        {races.data && (
          <CircuitPicker races={races.data} selected={selected} onSelect={setSelected} />
        )}
      </div>

      {validation.loading && <Loading label="Loading validation…" />}
      {validation.error && <ErrorNote message={validation.error} />}
      {validation.data && <ValidationDetail v={validation.data} />}
    </div>
  )
}
