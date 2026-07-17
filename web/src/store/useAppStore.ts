// App-wide UI state (selection, active layer, filters, sheet state).

import { create } from 'zustand'

import type { ChargerFilters, RouteResponse } from '../api/types'

export type MapLayer = 'chargers' | 'heat' | 'best-sites'
export type SheetState = 'peek' | 'expanded'

export interface SelectedPoint {
  lat: number
  lng: number
  label?: string
}

interface AppState {
  selected: SelectedPoint | null
  layer: MapLayer
  filters: ChargerFilters
  sheet: SheetState
  filtersOpen: boolean
  routeOpen: boolean
  route: RouteResponse | null
  select: (point: SelectedPoint) => void
  clearSelection: () => void
  setLayer: (layer: MapLayer) => void
  setFilters: (filters: Partial<ChargerFilters>) => void
  resetFilters: () => void
  setSheet: (sheet: SheetState) => void
  setFiltersOpen: (open: boolean) => void
  setRouteOpen: (open: boolean) => void
  setRoute: (route: RouteResponse | null) => void
}

const emptyFilters: ChargerFilters = { speed: null, network: null, connector: null }

export const useAppStore = create<AppState>((set) => ({
  selected: null,
  layer: 'chargers',
  filters: emptyFilters,
  sheet: 'peek',
  filtersOpen: false,
  routeOpen: false,
  route: null,
  select: (point) => set({ selected: point, sheet: 'peek' }),
  clearSelection: () => set({ selected: null }),
  setLayer: (layer) => set({ layer }),
  setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
  resetFilters: () => set({ filters: emptyFilters }),
  setSheet: (sheet) => set({ sheet }),
  setFiltersOpen: (filtersOpen) => set({ filtersOpen }),
  setRouteOpen: (routeOpen) => set({ routeOpen }),
  setRoute: (route) => set({ route }),
}))
