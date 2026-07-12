import { useEffect, useState } from 'react'

import { evaluateStrategy, getRaces, type EvaluateResponse } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { ConfigPanel } from '../components/dashboard/ConfigPanel'
import { Hero } from '../components/dashboard/Hero'
import { OutcomeDistribution } from '../components/dashboard/OutcomeDistribution'
import { StrategyBoard } from '../components/dashboard/StrategyBoard'
import { ErrorNote, Loading } from '../components/ui/Status'

type Metric = 'mean_s' | 'p90_s'

export function Dashboard() {
  const races = useAsync(getRaces, [])
  const [selected, setSelected] = useState<string>('')
  const [metric, setMetric] = useState<Metric>('mean_s')
  const [nSims, setNSims] = useState<number>(2000)

  // Default to the first generatable circuit once the race list arrives.
  useEffect(() => {
    if (!selected && races.data) {
      const first = races.data.find((r) => r.can_generate)
      if (first) setSelected(first.circuit_key)
    }
  }, [races.data, selected])

  const evaluation = useAsync<EvaluateResponse | null>(
    () =>
      selected
        ? evaluateStrategy({ circuit_key: selected, n_sims: nSims, robust_metric: metric })
        : Promise.resolve(null),
    [selected, metric, nSims],
  )

  return (
    <div className="space-y-8">
      {evaluation.data && <Hero result={evaluation.data} metric={metric} />}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[280px_1fr]">
        <div>
          {races.loading && <Loading label="Loading circuits…" />}
          {races.error && <ErrorNote message={races.error} />}
          {races.data && (
            <ConfigPanel
              races={races.data}
              selected={selected}
              onSelect={setSelected}
              metric={metric}
              onMetric={setMetric}
              nSims={nSims}
              onNSims={setNSims}
              scRate={evaluation.data?.sc_rate_per_lap ?? null}
            />
          )}
        </div>

        <div className="space-y-6">
          {evaluation.loading && <Loading label="Running Monte Carlo…" />}
          {evaluation.error && <ErrorNote message={evaluation.error} />}
          {evaluation.data && <StrategyBoard result={evaluation.data} />}
          {evaluation.data && <OutcomeDistribution result={evaluation.data} />}
        </div>
      </div>
    </div>
  )
}
