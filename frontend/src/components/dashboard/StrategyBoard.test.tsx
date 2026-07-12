import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { EvaluateResponse, StrategyOut } from '../../lib/api'
import { StrategyBoard } from './StrategyBoard'

function strat(
  key: string,
  compounds: string[],
  pitLaps: number[],
  mean: number,
  win: number,
): StrategyOut {
  return {
    key,
    n_stops: pitLaps.length,
    pit_laps: pitLaps,
    compounds,
    win_probability: win,
    histogram: new Array(32).fill(0),
    breakdown: {
      base_s: 5400,
      compound_offset_s: 0,
      degradation_s: 200,
      fuel_s: -50,
      pit_s: 44,
      total_s: 5594,
    },
    distribution: {
      mean_s: mean,
      std_s: 50,
      p10_s: mean - 40,
      p50_s: mean,
      p90_s: mean + 40,
      best_s: mean - 70,
      worst_s: mean + 80,
      sc_benefit_freq: 0.2,
      n_sims: 1000,
    },
  }
}

const result: EvaluateResponse = {
  circuit_key: 'bahrain',
  total_laps: 57,
  sc_rate_per_lap: 0.08,
  n_strategies_generated: 8000,
  deterministic_top_key: 'S-M-H@14,36',
  robust_top_key: 'S-M-H@14,36',
  strategies: [
    strat('S-M-H@14,36', ['SOFT', 'MEDIUM', 'HARD'], [14, 36], 5651, 0.6),
    strat('S-H-S@20,41', ['SOFT', 'HARD', 'SOFT'], [20, 41], 5654, 0.4),
  ],
  histogram_lo: 5590,
  histogram_hi: 5730,
  runtime_ms: 200,
  generated_at: '',
}

describe('StrategyBoard', () => {
  it('renders every strategy and highlights exactly one (the fastest)', () => {
    const { container } = render(<StrategyBoard result={result} />)
    expect(container.textContent).toContain('S-M-H@14,36')
    expect(container.textContent).toContain('S-H-S@20,41')
    expect(container.querySelectorAll('[class*="border-l-fastest"]')).toHaveLength(1)
  })
})
