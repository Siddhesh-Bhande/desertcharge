import type { MapLayer } from '../store/useAppStore'

const OPTIONS: readonly { value: MapLayer; label: string }[] = [
  { value: 'chargers', label: 'Chargers' },
  { value: 'heat', label: 'Heat' },
  { value: 'best-sites', label: 'Best sites' },
]

interface LayerToggleProps {
  value: MapLayer
  onChange: (layer: MapLayer) => void
}

export function LayerToggle({ value, onChange }: LayerToggleProps) {
  return (
    <div
      role="tablist"
      aria-label="Map layer"
      className="flex gap-0.5 rounded-full bg-basalt-800/95 p-1 shadow-lg backdrop-blur"
    >
      {OPTIONS.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className={
              'rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors ' +
              (active ? 'bg-brass-400 text-ironwood-900' : 'text-bone-100/60 hover:text-bone-100')
            }
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
