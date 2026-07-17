import { scoreBands } from '../lib/tokens'

const RANGES = ['0-20', '21-40', '41-60', '61-80', '81-100']

export function Legend() {
  return (
    <div className="rounded-xl bg-basalt-800/95 p-3.5 shadow-lg backdrop-blur">
      <div className="mb-2 font-mono text-[9px] uppercase tracking-[0.16em] text-bone-100/50">
        Desert score
      </div>
      <ul className="flex flex-col gap-1.5">
        {scoreBands.map((band, index) => (
          <li key={band.label} className="flex items-center gap-2">
            <span
              className="h-3.5 w-3.5 rounded-sm"
              style={{ background: band.color }}
              aria-hidden
            />
            <span className="font-mono text-[11px] text-bone-100">{band.label}</span>
            <span className="ml-auto font-mono text-[10px] text-bone-100/45">{RANGES[index]}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
