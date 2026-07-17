// TanStack Query hooks over the API client.

import { useQuery } from '@tanstack/react-query'

import { fetchBestSites, fetchChargers, fetchGrid, fetchScore } from './client'
import type { Bbox, ChargerFilters } from './types'

export function useScore(point: { lat: number; lng: number } | null) {
  return useQuery({
    queryKey: ['score', point?.lat, point?.lng],
    queryFn: () => fetchScore(point!.lat, point!.lng),
    enabled: point !== null,
    staleTime: 5 * 60 * 1000,
  })
}

export function useChargers(bbox: Bbox | null, filters: ChargerFilters, enabled: boolean) {
  return useQuery({
    queryKey: ['chargers', bbox, filters],
    queryFn: () => fetchChargers(bbox!, filters),
    enabled: enabled && bbox !== null,
    staleTime: 60 * 1000,
  })
}

export function useBestSites(enabled: boolean) {
  return useQuery({
    queryKey: ['best-sites'],
    queryFn: () => fetchBestSites(10),
    enabled,
    staleTime: 30 * 60 * 1000,
  })
}

export function useGrid(enabled: boolean) {
  return useQuery({
    queryKey: ['grid'],
    queryFn: fetchGrid,
    enabled,
    staleTime: Infinity,
  })
}
