import { describe, expect, it } from 'vitest'

import { bandForScore, scoreColorRgba } from './tokens'

describe('bandForScore', () => {
  it('maps score ranges to bands', () => {
    expect(bandForScore(0).label).toBe('served')
    expect(bandForScore(20).label).toBe('served')
    expect(bandForScore(21).label).toBe('good')
    expect(bandForScore(55).label).toBe('moderate')
    expect(bandForScore(80).label).toBe('poor')
    expect(bandForScore(81).label).toBe('desert')
    expect(bandForScore(100).label).toBe('desert')
  })
})

describe('scoreColorRgba', () => {
  it('returns the desert band color for a high score', () => {
    expect(scoreColorRgba(90)).toEqual([178, 58, 36, 180])
  })

  it('applies the given alpha', () => {
    expect(scoreColorRgba(10, 120)[3]).toBe(120)
  })
})
