import { useEffect, useState } from 'react'

import { generateReport, getRaces, reportPdfUrl, type ReportResponse } from '../lib/api'
import { formatPct, formatRaceTime, formatSeconds } from '../lib/format'
import { useAsync } from '../lib/hooks'
import { stintsFromStrategy } from '../lib/stints'
import type { Compound } from '../lib/tyres'
import { CircuitPicker } from '../components/validation/CircuitPicker'
import { ConfidenceRibbon } from '../components/charts/ConfidenceRibbon'
import { StintTimeline } from '../components/charts/StintTimeline'
import { Button } from '../components/ui/Button'
import { Panel } from '../components/ui/Panel'
import { ErrorNote, Loading } from '../components/ui/Status'
import { TyreSequence } from '../components/ui/TyreChip'

function ReportPreview({ report }: { report: ReportResponse }) {
  const rec = report.recommendation
  const v = report.validation
  const d = rec.distribution
  const recStints = stintsFromStrategy(rec.pit_laps, rec.compounds, v.total_laps)
  const actualStints = stintsFromStrategy(v.actual.pit_laps, v.actual.compounds, v.total_laps)

  return (
    <Panel>
      <div className="space-y-8 p-2">
        <div className="border-b border-hairline pb-5">
          <h2 className="font-display text-3xl font-bold text-ink">Race Strategy Report</h2>
          <p className="mt-1 font-body text-sm text-muted">
            {report.circuit_key} · {v.total_laps} laps
          </p>
        </div>

        <section className="space-y-2">
          <h3 className="font-body text-[11px] uppercase tracking-wider text-muted">
            Executive summary
          </h3>
          <p className="rounded-panel border border-hairline bg-base/40 px-5 py-4 font-body text-sm leading-relaxed text-ink">
            {report.executive_summary}
          </p>
          <p className="border-l-2 border-fastest pl-3 font-body text-xs text-muted">
            <span className="font-mono text-fastest">
              {formatPct(report.recommendation.win_probability)}
            </span>{' '}
            — {report.confidence_note}
          </p>
        </section>

        <section className="space-y-3">
          <h3 className="font-display text-sm font-semibold text-ink">Recommended strategy</h3>
          <div className="flex flex-wrap items-center gap-6">
            <TyreSequence compounds={rec.compounds as Compound[]} />
            <div>
              <div className="font-body text-[11px] uppercase tracking-wider text-muted">
                Finish
              </div>
              <div className="font-mono text-lg text-ink">{formatRaceTime(d.mean_s)}</div>
            </div>
            <div>
              <div className="font-body text-[11px] uppercase tracking-wider text-muted">
                Confidence
              </div>
              <div className="font-mono text-lg text-fastest">{formatPct(rec.win_probability)}</div>
            </div>
            <div className="min-w-[180px] flex-1">
              <ConfidenceRibbon
                best={d.best_s}
                p10={d.p10_s}
                mean={d.mean_s}
                p90={d.p90_s}
                worst={d.worst_s}
                domainLo={d.best_s}
                domainHi={d.worst_s}
                fastest
                size="md"
              />
            </div>
          </div>
          <StintTimeline stints={recStints} totalLaps={v.total_laps} variant="large" />
        </section>

        <section className="space-y-3 border-t border-hairline pt-4">
          <h3 className="font-display text-sm font-semibold text-ink">
            Predicted vs. actual ({v.actual.winner})
          </h3>
          <StintTimeline stints={recStints} totalLaps={v.total_laps} label="Engine" />
          <StintTimeline
            stints={actualStints}
            totalLaps={v.total_laps}
            label={`Actual (${v.actual.winner})`}
          />
          <p className="font-mono text-xs text-muted">
            First-stop error {v.metrics.first_stop_abs_error} laps · timing{' '}
            {formatSeconds(v.timing.time_error_s, 1)} · {report.explanation}
          </p>
        </section>
      </div>
    </Panel>
  )
}

export function ReportView() {
  const races = useAsync(getRaces, [])
  const [selected, setSelected] = useState<string>('')

  useEffect(() => {
    if (!selected && races.data) {
      const first = races.data.find((r) => r.can_generate)
      if (first) setSelected(first.circuit_key)
    }
  }, [races.data, selected])

  const report = useAsync<ReportResponse | null>(
    () => (selected ? generateReport({ circuit_key: selected }) : Promise.resolve(null)),
    [selected],
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <h1 className="font-display text-xl font-semibold text-ink">Report</h1>
        <div className="flex items-center gap-4">
          {races.data && (
            <CircuitPicker races={races.data} selected={selected} onSelect={setSelected} />
          )}
          <Button
            variant="primary"
            onClick={() => selected && window.open(reportPdfUrl(selected), '_blank')}
            disabled={!report.data}
            title="Download the report as a PDF"
          >
            Export PDF
          </Button>
        </div>
      </div>

      {report.loading && <Loading label="Generating report…" />}
      {report.error && <ErrorNote message={report.error} />}
      {report.data && <ReportPreview report={report.data} />}
    </div>
  )
}
