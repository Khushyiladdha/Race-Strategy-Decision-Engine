import { afterEach, describe, expect, it, vi } from 'vitest'

import { evaluateStrategy, getRaces } from './api'

afterEach(() => vi.restoreAllMocks())

describe('api client', () => {
  it('GETs the versioned races path', async () => {
    const races = [
      {
        id: 1,
        year: 2023,
        round: 1,
        circuit_key: 'bahrain',
        can_generate: true,
        reason: '',
        total_laps: 57,
      },
    ]
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => races })
    vi.stubGlobal('fetch', fetchMock)

    const out = await getRaces()
    expect(out).toEqual(races)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/races')
  })

  it('surfaces the API detail message on error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ detail: 'two-compound rule' }),
      }),
    )
    await expect(evaluateStrategy({ circuit_key: 'australian' })).rejects.toThrow(
      'two-compound rule',
    )
  })
})
