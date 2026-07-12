import type { ReactNode } from 'react'

import { Panel } from '../ui/Panel'
import type { RaceListItem } from '../../lib/api'
import { formatPct } from '../../lib/format'

type Metric = 'mean_s' | 'p90_s'

interface ConfigPanelProps {
  races: RaceListItem[]
  selected: string
  onSelect: (circuit: string) => void
  metric: Metric
  onMetric: (m: Metric) => void
  nSims: number
  onNSims: (n: number) => void
  scRate: number | null
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="font-body text-[11px] uppercase tracking-wider text-muted">{label}</span>
      {children}
    </label>
  )
}

function Segmented<T extends string | number>({
  options,
  value,
  onChange,
  fmt,
}: {
  options: T[]
  value: T
  onChange: (v: T) => void
  fmt: (v: T) => string
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-chip border border-hairline">
      {options.map((o) => (
        <button
          key={String(o)}
          onClick={() => onChange(o)}
          className={`px-3 py-1.5 font-body text-xs transition-colors ${
            o === value ? 'bg-surface-raised text-ink' : 'text-muted hover:text-ink'
          }`}
        >
          {fmt(o)}
        </button>
      ))}
    </div>
  )
}

function Assumption({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="font-body text-xs text-muted">{label}</span>
      <span className="font-mono text-xs text-ink">{value}</span>
    </div>
  )
}

export function ConfigPanel({
  races,
  selected,
  onSelect,
  metric,
  onMetric,
  nSims,
  onNSims,
  scRate,
}: ConfigPanelProps) {
  const generatable = races.filter((r) => r.can_generate)

  return (
    <Panel title="Configuration">
      <div className="space-y-5">
        <Field label="Circuit">
          <select
            value={selected}
            onChange={(e) => onSelect(e.target.value)}
            className="w-full rounded-chip border border-hairline bg-surface-raised px-3 py-2 font-body text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gain/60"
          >
            {generatable.map((r) => (
              <option key={r.circuit_key} value={r.circuit_key}>
                {r.circuit_key} ({r.total_laps} laps)
              </option>
            ))}
          </select>
        </Field>

        <Field label="Ranking metric">
          <Segmented<Metric>
            options={['mean_s', 'p90_s']}
            value={metric}
            onChange={onMetric}
            fmt={(m) => (m === 'mean_s' ? 'Mean' : 'P90 (risk-averse)')}
          />
        </Field>

        <Field label="Simulations">
          <Segmented<number>
            options={[1000, 2000, 5000]}
            value={nSims}
            onChange={onNSims}
            fmt={(n) => n.toLocaleString()}
          />
        </Field>

        <div className="space-y-2 border-t border-hairline pt-4">
          <span className="font-body text-[11px] uppercase tracking-wider text-muted">
            Assumptions (read-only)
          </span>
          <Assumption
            label="Safety-car rate / lap"
            value={scRate === null ? '—' : formatPct(scRate)}
          />
          <Assumption label="Fuel model" value="linear, constant" />
          <Assumption label="Tyre data" value="2023 fitted" />
        </div>
      </div>
    </Panel>
  )
}
