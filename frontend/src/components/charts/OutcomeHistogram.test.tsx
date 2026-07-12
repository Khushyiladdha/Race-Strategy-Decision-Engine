import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { OutcomeHistogram } from './OutcomeHistogram'

describe('OutcomeHistogram', () => {
  it('renders one rect per bin per series', () => {
    const counts = Array.from({ length: 32 }, (_, i) => i)
    const { container } = render(
      <OutcomeHistogram
        lo={5600}
        hi={5730}
        series={[
          { counts, fastest: true, label: 'best' },
          { counts, fastest: false, label: '2nd' },
        ]}
      />,
    )
    expect(container.querySelectorAll('rect')).toHaveLength(64)
    // only the fastest series uses the purple accent
    expect(container.querySelectorAll('[class*="fill-fastest"]')).toHaveLength(1)
  })
})
