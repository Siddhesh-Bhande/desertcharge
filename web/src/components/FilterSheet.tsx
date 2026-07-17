import type { ChargerFilters } from '../api/types'
import { useAppStore } from '../store/useAppStore'

const NETWORKS = ['Electrify America', 'Tesla', 'ChargePoint', 'EVgo']
const CONNECTORS = ['CCS', 'NACS', 'CHAdeMO', 'J1772']

interface ChipProps {
  label: string
  active: boolean
  onClick: () => void
}

function Chip({ label, active, onClick }: ChipProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={
        'rounded-full px-3.5 py-2 text-sm transition-colors ' +
        (active
          ? 'bg-brass-400 font-semibold text-ironwood-900'
          : 'border border-bone-100/30 text-bone-100')
      }
    >
      {label}
    </button>
  )
}

export function FilterSheet() {
  const filters = useAppStore((state) => state.filters)
  const setFilters = useAppStore((state) => state.setFilters)
  const resetFilters = useAppStore((state) => state.resetFilters)
  const close = useAppStore((state) => state.setFiltersOpen)

  const toggle = <K extends keyof ChargerFilters>(key: K, value: ChargerFilters[K]) =>
    setFilters({ [key]: filters[key] === value ? null : value } as Partial<ChargerFilters>)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-baseline justify-between">
        <h2
          className="font-display text-xl font-bold text-bone-100"
          style={{ fontStretch: '125%' }}
        >
          Filters
        </h2>
        <button
          type="button"
          onClick={resetFilters}
          className="text-sm font-semibold text-brass-400"
        >
          Reset
        </button>
      </div>

      <Group label="Speed">
        <Chip
          label="DC fast"
          active={filters.speed === 'dc'}
          onClick={() => toggle('speed', 'dc')}
        />
        <Chip
          label="Level 2"
          active={filters.speed === 'level2'}
          onClick={() => toggle('speed', 'level2')}
        />
      </Group>

      <Group label="Network">
        {NETWORKS.map((network) => (
          <Chip
            key={network}
            label={network}
            active={filters.network === network}
            onClick={() => toggle('network', network)}
          />
        ))}
      </Group>

      <Group label="Connector">
        {CONNECTORS.map((connector) => (
          <Chip
            key={connector}
            label={connector}
            active={filters.connector === connector}
            onClick={() => toggle('connector', connector)}
          />
        ))}
      </Group>

      <button
        type="button"
        onClick={() => close(false)}
        className="h-13 rounded-2xl bg-brass-400 text-base font-bold text-ironwood-900"
      >
        Show chargers
      </button>
    </div>
  )
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-bone-100/50">
        {label}
      </div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  )
}
