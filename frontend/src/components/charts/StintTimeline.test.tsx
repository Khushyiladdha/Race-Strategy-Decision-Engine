import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { stintsFromStrategy } from '../../lib/stints'
import { StintTimeline } from './StintTimeline'

describe('StintTimeline', () => {
  it('renders one bar per stint', () => {
    const stints = stintsFromStrategy([14, 36], ['SOFT', 'SOFT', 'HARD'], 57)
    const { container } = render(<StintTimeline stints={stints} totalLaps={57} />)
    expect(container.querySelectorAll('rect')).toHaveLength(3)
  })
})
