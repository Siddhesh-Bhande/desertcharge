import type { Charger, ScoreResponse } from '../api/types'
import { formatCount, formatMiles } from '../lib/format'
import { ChargerList } from './ChargerList'
import { HexGauge } from './HexGauge'

interface ScorePanelProps {
  score: ScoreResponse
  point: { lat: number; lng: number; label?: string }
  chargers: Charger[]
  expanded: boolean
}

function Readout({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <div className="flex flex-1 flex-col items-center gap-1.5 px-2 py-3">
      <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-bone-100/50">
        {label}
      </span>
      <span
        className={
          'font-mono text-base font-semibold ' + (alert ? 'text-rust-600' : 'text-bone-100')
        }
      >
        {value}
      </span>
    </div>
  )
}

export function ScorePanel({ score, point, chargers, expanded }: ScorePanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-5">
        <HexGauge score={score.score} size={expanded ? 76 : 88} />
        <div className="flex flex-col gap-2">
          {point.label && (
            <span
              className="font-display text-lg font-bold text-bone-100"
              style={{ fontStretch: '125%' }}
            >
              {point.label}
            </span>
          )}
          <p className="text-[15px] leading-snug text-bone-100/85">{score.verdict}</p>
        </div>
      </div>

      {expanded && (
        <>
          <div className="flex divide-x divide-bone-100/15 rounded-2xl border border-bone-100/15">
            <Readout label="Pop served" value={formatCount(score.population)} />
            <Readout
              label="Nearest DCFC"
              value={formatMiles(score.nearest_dc_fast_miles)}
              alert={score.nearest_dc_fast_miles === null || score.nearest_dc_fast_miles > 25}
            />
            <Readout
              label="Ports 10 mi"
              value={String(Math.round(score.chargers_10mi))}
              alert={score.chargers_10mi === 0}
            />
          </div>

          <div>
            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-bone-100/50">
              Nearby chargers
            </div>
            <ChargerList chargers={chargers} origin={point} />
          </div>
        </>
      )}
    </div>
  )
}
