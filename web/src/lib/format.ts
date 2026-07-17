export function formatMiles(miles: number | null): string {
  if (miles === null) return 'none nearby'
  if (miles > 900) return '900+ mi'
  return `${Math.round(miles)} mi`
}

export function formatPower(kw: number | null): string {
  if (kw === null) return 'unknown'
  return `${Math.round(kw)} kW`
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat('en-US').format(Math.round(value))
}
