// Design tokens mirrored for use in JS (deck.gl colors, score scale).
// Source of truth: docs/design/design-tokens.md.

export const colors = {
  basalt900: '#12151A',
  basalt800: '#1A1D22',
  basalt700: '#22262C',
  bone100: '#E9E3D6',
  ironwood900: '#241F1A',
  clay600: '#6B6152',
  brass400: '#C9A467',
  rust600: '#B4552F',
  teal600: '#2E6E75',
} as const

export interface ScoreBand {
  readonly label: string
  readonly color: string
  readonly max: number
}

// Cool served to hot desert. Always paired with the number and label.
export const scoreBands: readonly ScoreBand[] = [
  { label: 'served', color: '#1B9E8A', max: 20 },
  { label: 'good', color: '#7FB069', max: 40 },
  { label: 'moderate', color: '#E6B23A', max: 60 },
  { label: 'poor', color: '#D57A33', max: 80 },
  { label: 'desert', color: '#B23A24', max: 100 },
]

export function bandForScore(score: number): ScoreBand {
  return scoreBands.find((band) => score <= band.max) ?? scoreBands[scoreBands.length - 1]!
}

/** RGBA tuple for a score, for deck.gl fill colors. */
export function scoreColorRgba(score: number, alpha = 180): [number, number, number, number] {
  const hex = bandForScore(score).color
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b, alpha]
}
