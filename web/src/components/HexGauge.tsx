import { bandForScore } from '../lib/tokens'

interface HexGaugeProps {
  score: number
  size?: number
}

// The signature element: an H3-shaped hexagon filled by the desert-score band.
export function HexGauge({ score, size = 88 }: HexGaugeProps) {
  const band = bandForScore(score)
  return (
    <div className="flex flex-none flex-col items-center gap-2">
      <div
        role="img"
        aria-label={`Desert score ${score} out of 100, ${band.label}`}
        style={{
          width: size,
          height: size * 1.14,
          clipPath: 'polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%)',
          background: band.color,
        }}
        className="flex items-center justify-center"
      >
        <span
          className="font-display font-extrabold text-basalt-900"
          style={{ fontStretch: '125%', fontSize: size * 0.4 }}
        >
          {score}
        </span>
      </div>
      <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-bone-100">
        {band.label}
      </span>
    </div>
  )
}
