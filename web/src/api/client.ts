// Typed fetch wrappers for the DesertCharge API.

import type {
  BestSite,
  Bbox,
  Charger,
  ChargerFilters,
  GeocodeResult,
  HexScore,
  RouteResponse,
  ScoreResponse,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const GRID_URL = import.meta.env.VITE_GRID_URL ?? '/grid.json'

async function getJson<T>(path: string, params: Record<string, string>): Promise<T> {
  const query = new URLSearchParams(params).toString()
  const response = await fetch(`${API_BASE}${path}?${query}`)
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchScore(lat: number, lng: number): Promise<ScoreResponse> {
  return getJson<ScoreResponse>('/api/score', {
    lat: String(lat),
    lng: String(lng),
  })
}

export function fetchChargers(bbox: Bbox, filters: ChargerFilters): Promise<Charger[]> {
  const params: Record<string, string> = {
    min_lat: String(bbox.minLat),
    min_lng: String(bbox.minLng),
    max_lat: String(bbox.maxLat),
    max_lng: String(bbox.maxLng),
  }
  if (filters.speed) params.speed = filters.speed
  if (filters.network) params.network = filters.network
  if (filters.connector) params.connector = filters.connector
  return getJson<Charger[]>('/api/chargers', params)
}

export function fetchBestSites(limit = 10): Promise<BestSite[]> {
  return getJson<BestSite[]>('/api/best-sites', { limit: String(limit) })
}

export function fetchGeocode(query: string): Promise<GeocodeResult[]> {
  return getJson<GeocodeResult[]>('/api/geocode', { q: query })
}

export async function fetchRoute(
  origin: { lat: number; lng: number },
  destination: { lat: number; lng: number },
): Promise<RouteResponse> {
  const response = await fetch(`${API_BASE}/api/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin: [origin.lat, origin.lng],
      destination: [destination.lat, destination.lng],
    }),
  })
  if (!response.ok) {
    throw new Error(`Route request failed with ${response.status}`)
  }
  return (await response.json()) as RouteResponse
}

/** The static scored grid for the heat layer. Absent in dev is fine (empty). */
export async function fetchGrid(): Promise<HexScore[]> {
  const response = await fetch(GRID_URL)
  if (!response.ok) return []
  return (await response.json()) as HexScore[]
}
