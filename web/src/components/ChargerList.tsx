import type { Charger } from '../api/types'
import { formatMiles, formatPower } from '../lib/format'

function distanceMiles(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(b.lat - a.lat)
  const dLng = toRad(b.lng - a.lng)
  const lat1 = toRad(a.lat)
  const lat2 = toRad(b.lat)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2
  return 3958.8 * 2 * Math.asin(Math.sqrt(h))
}

interface ChargerListProps {
  chargers: Charger[]
  origin: { lat: number; lng: number }
}

export function ChargerList({ chargers, origin }: ChargerListProps) {
  const nearest = [...chargers]
    .map((charger) => ({ charger, miles: distanceMiles(origin, charger) }))
    .sort((a, b) => a.miles - b.miles)
    .slice(0, 8)

  if (nearest.length === 0) {
    return (
      <p className="px-1 py-6 text-sm text-bone-100/60">
        No chargers loaded in view. Move the map or widen your filters.
      </p>
    )
  }

  return (
    <ul className="flex flex-col gap-1.5">
      {nearest.map(({ charger, miles }) => (
        <li
          key={charger.id}
          className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 hover:bg-brass-400/5"
        >
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="truncate text-sm font-semibold text-bone-100">
              {charger.network ?? 'Independent'}
            </span>
            <span className="truncate text-xs text-bone-100/55">
              {charger.name ?? 'Charging station'}
            </span>
          </div>
          <div className="flex flex-none flex-col items-end gap-1">
            <span className="font-mono text-xs text-bone-100">{formatPower(charger.power_kw)}</span>
            <span className="font-mono text-[11px] text-bone-100/50">{formatMiles(miles)}</span>
          </div>
          <div className="flex flex-none gap-1">
            {charger.connector_types.slice(0, 2).map((connector) => (
              <span
                key={connector}
                className="rounded border border-bone-100/25 px-1.5 py-0.5 font-mono text-[9px] tracking-[0.08em] text-bone-100/70"
              >
                {connector}
              </span>
            ))}
          </div>
        </li>
      ))}
    </ul>
  )
}
