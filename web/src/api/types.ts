// Response shapes returned by the DesertCharge API.

export interface ScoreResponse {
  score: number
  band: string
  verdict: string
  population: number
  nearest_dc_fast_miles: number | null
  chargers_10mi: number
  hex_index: string
  exact: boolean
}

export interface Charger {
  id: number
  name: string | null
  network: string | null
  power_kw: number | null
  connector_types: string[]
  is_dc_fast: boolean
  lat: number
  lng: number
}

export interface BestSite {
  rank: number
  lat: number
  lng: number
  est_population_served: number
  gap_miles_closed: number
  reason: string | null
}

export interface GeocodeResult {
  name: string
  lat: number
  lng: number
  kind: string | null
}

export interface HexScore {
  h3: string
  score: number
}

export interface Bbox {
  minLat: number
  minLng: number
  maxLat: number
  maxLng: number
}

export interface ChargerFilters {
  speed: 'dc' | 'level2' | null
  network: string | null
  connector: string | null
}
