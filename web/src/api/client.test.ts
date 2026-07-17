import { afterEach, describe, expect, it, vi } from 'vitest'

import { fetchChargers, fetchScore } from './client'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fetchScore', () => {
  it('calls the score endpoint with coordinates and returns the body', async () => {
    const body = { score: 84, band: 'desert' }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => body })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchScore(35, -116)

    const url = fetchMock.mock.calls[0]?.[0] as string
    expect(url).toContain('/api/score?')
    expect(url).toContain('lat=35')
    expect(url).toContain('lng=-116')
    expect(result.score).toBe(84)
  })

  it('throws on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    await expect(fetchScore(1, 2)).rejects.toThrow()
  })
})

describe('fetchChargers', () => {
  it('includes only the filters that are set', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] })
    vi.stubGlobal('fetch', fetchMock)

    await fetchChargers(
      { minLat: 34, minLng: -117, maxLat: 36, maxLng: -115 },
      { speed: 'dc', network: null, connector: null },
    )

    const url = fetchMock.mock.calls[0]?.[0] as string
    expect(url).toContain('speed=dc')
    expect(url).not.toContain('network=')
  })
})
