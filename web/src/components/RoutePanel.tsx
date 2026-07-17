import { useState } from 'react'

import { fetchRoute } from '../api/client'
import { useAppStore } from '../store/useAppStore'
import { CorridorStrip } from './CorridorStrip'
import { PlaceInput } from './PlaceInput'

type Place = { lat: number; lng: number; label: string }

export function RoutePanel() {
  const route = useAppStore((state) => state.route)
  const setRoute = useAppStore((state) => state.setRoute)
  const setRouteOpen = useAppStore((state) => state.setRouteOpen)
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  async function findRoute() {
    if (!origin || !destination) return
    setLoading(true)
    setError(false)
    try {
      setRoute(await fetchRoute(origin, destination))
    } catch {
      setError(true)
      setRoute(null)
    } finally {
      setLoading(false)
    }
  }

  function close() {
    setRoute(null)
    setRouteOpen(false)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h2
          className="font-display text-xl font-bold text-bone-100"
          style={{ fontStretch: '125%' }}
        >
          Plan a drive
        </h2>
        <button type="button" onClick={close} className="text-sm font-semibold text-brass-400">
          Close
        </button>
      </div>

      <PlaceInput label="From" placeholder="Start" onSelect={setOrigin} />
      <PlaceInput label="To" placeholder="Destination" onSelect={setDestination} />

      <button
        type="button"
        onClick={() => void findRoute()}
        disabled={!origin || !destination || loading}
        className="h-12 rounded-2xl bg-brass-400 text-base font-bold text-ironwood-900 disabled:opacity-40"
      >
        {loading ? 'Finding route...' : 'Score the drive'}
      </button>

      {error && (
        <p className="text-sm text-rust-600">Could not find a route. Try different places.</p>
      )}
      {route && <CorridorStrip route={route} />}
    </div>
  )
}
