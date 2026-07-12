import { describe, expect, it } from 'vitest'

import { stintsFromStrategy } from './stints'

describe('stintsFromStrategy', () => {
  it('reconstructs a 2-stop that tiles 1..N', () => {
    expect(stintsFromStrategy([14, 36], ['SOFT', 'SOFT', 'HARD'], 57)).toEqual([
      { compound: 'SOFT', startLap: 1, endLap: 14 },
      { compound: 'SOFT', startLap: 15, endLap: 36 },
      { compound: 'HARD', startLap: 37, endLap: 57 },
    ])
  })

  it('handles a 1-stop', () => {
    const s = stintsFromStrategy([18], ['SOFT', 'HARD'], 57)
    expect(s).toHaveLength(2)
    expect(s[0].endLap).toBe(18)
    expect(s[1].endLap).toBe(57)
  })

  it('leaves no gaps or overlaps', () => {
    const s = stintsFromStrategy([20, 40], ['MEDIUM', 'HARD', 'SOFT'], 60)
    for (let i = 1; i < s.length; i++) {
      expect(s[i].startLap).toBe(s[i - 1].endLap + 1)
    }
    expect(s[s.length - 1].endLap).toBe(60)
  })
})
