import { useEffect, useState } from 'react'

import { getDegradation, getRaces, type DegradationResponse } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { DegradationChart } from '../components/charts/DegradationChart'
import { CircuitPicker } from '../components/validation/CircuitPicker'
import { Panel } from '../components/ui/Panel'
import { ErrorNote, Loading } from '../components/ui/Status'

export function Insights() {
  const races = useAsync(getRaces, [])
  const [selected, setSelected] = useState<string>('')

  useEffect(() => {
    if (!selected && races.data) {
      const first = races.data.find((r) => r.can_generate)
      if (first) setSelected(first.circuit_key)
    }
  }, [races.data, selected])

  const deg = useAsync<DegradationResponse | null>(
    () => (selected ? getDegradation(selected) : Promise.resolve(null)),
    [selected],
  )

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h1 className="font-display text-xl font-semibold text-ink">Model insights</h1>
        <p className="max-w-2xl font-body text-sm text-muted">
          The tyre-degradation model is a per-compound curve{' '}
          <span className="font-mono text-ink">deg(n) = a·n + b·n²</span>, fit to real 2023 stint
          laps with <span className="font-mono text-ink">scipy.optimize.curve_fit</span>.
          Coefficients are constrained to <span className="font-mono text-ink">a, b ≥ 0</span> so
          the model is monotonic — a tyre only ever gets slower — which the unconstrained fit
          doesn't guarantee.
        </p>
        {races.data && (
          <CircuitPicker races={races.data} selected={selected} onSelect={setSelected} />
        )}
      </div>

      <Panel title="Tyre degradation — predicted lap-time loss vs. fresh tyre">
        {deg.loading && <Loading label="Loading curves…" />}
        {deg.error && <ErrorNote message={deg.error} />}
        {deg.data && <DegradationChart compounds={deg.data.compounds} />}
      </Panel>
    </div>
  )
}
