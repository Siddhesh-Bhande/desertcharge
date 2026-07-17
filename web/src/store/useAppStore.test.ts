import { beforeEach, describe, expect, it } from 'vitest'

import { useAppStore } from './useAppStore'

beforeEach(() => {
  useAppStore.setState({
    selected: null,
    layer: 'chargers',
    filters: { speed: null, network: null, connector: null },
    sheet: 'peek',
    filtersOpen: false,
  })
})

describe('useAppStore', () => {
  it('selecting a point resets the sheet to peek', () => {
    useAppStore.getState().setSheet('expanded')
    useAppStore.getState().select({ lat: 35, lng: -116 })
    expect(useAppStore.getState().selected).toEqual({ lat: 35, lng: -116 })
    expect(useAppStore.getState().sheet).toBe('peek')
  })

  it('merges and resets filters', () => {
    useAppStore.getState().setFilters({ speed: 'dc' })
    useAppStore.getState().setFilters({ network: 'EVgo' })
    expect(useAppStore.getState().filters).toEqual({
      speed: 'dc',
      network: 'EVgo',
      connector: null,
    })
    useAppStore.getState().resetFilters()
    expect(useAppStore.getState().filters.speed).toBeNull()
  })
})
