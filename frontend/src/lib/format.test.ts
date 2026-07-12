import { describe, expect, it } from 'vitest'

import { formatDelta, formatLapTime, formatPct, formatRaceTime, formatSeconds } from './format'

describe('format', () => {
  it('lap time as m:ss.mmm', () => {
    expect(formatLapTime(94.512)).toBe('1:34.512')
  })

  it('delta carries sign and marks zero', () => {
    expect(formatDelta(2.3)).toBe('+2.30')
    expect(formatDelta(-0.85)).toBe('-0.85')
    expect(formatDelta(0)).toBe('±0.00')
  })

  it('percent rounds', () => {
    expect(formatPct(0.94)).toBe('94%')
    expect(formatPct(0.286)).toBe('29%')
  })

  it('race time as h:mm:ss', () => {
    expect(formatRaceTime(5651.24)).toBe('1:34:11')
  })

  it('seconds with fixed digits', () => {
    expect(formatSeconds(5651.24, 0)).toBe('5651s')
  })
})
