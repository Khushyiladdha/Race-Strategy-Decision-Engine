import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DegradationCurve } from '../../lib/api'
import { DegradationChart } from './DegradationChart'

function curve(compound: string, a: number): DegradationCurve {
  return {
    compound,
    a,
    b: 0.001,
    max_observed: 20,
    curve: Array.from({ length: 20 }, (_, i) => ({ lap: i + 1, loss_s: a * (i + 1) })),
  }
}

describe('DegradationChart', () => {
  it('renders one line per compound', () => {
    const { container } = render(
      <DegradationChart compounds={[curve('SOFT', 0.12), curve('HARD', 0.05)]} />,
    )
    expect(container.querySelectorAll('path')).toHaveLength(2)
  })
})
