import type { RouteResponse } from '../api/types'
import { corridorColor } from '../lib/tokens'

export function CorridorStrip({ route }: { route: RouteResponse }) {
  const gap = Math.round(route.worst_gap_miles)
  return (
    <div className="flex flex-col gap-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-bone-100/50">
        Corridor · {Math.round(route.distance_miles)} mi
      </div>
      <div
        className="flex h-4.5 overflow-hidden rounded-full"
        role="img"
        aria-label={`Charging access along the drive. Worst desert gap ${gap} miles.`}
      >
        {route.samples.map((sample) => (
          <span
            key={sample.fraction}
            className="flex-1"
            style={{ background: corridorColor(sample.nearest_dc_fast_miles) }}
          />
        ))}
      </div>
      <div className="flex items-center gap-2">
        <span className="h-3 w-3 flex-none rounded-sm bg-score-desert" aria-hidden />
        <span className="text-sm font-semibold text-bone-100">
          {gap > 0 ? `Worst desert gap: ${gap} mi` : 'Fast charging the whole way'}
        </span>
      </div>
    </div>
  )
}
