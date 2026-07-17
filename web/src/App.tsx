import { lazy, Suspense, useState } from 'react'

import { useBestSites, useChargers, useGrid, useScore } from './api/hooks'
import type { Bbox } from './api/types'
import { BottomSheet } from './components/BottomSheet'
import { FilterSheet } from './components/FilterSheet'
import { LayerToggle } from './components/LayerToggle'
import { Legend } from './components/Legend'
import { ScorePanel } from './components/ScorePanel'
import { SearchBar } from './components/SearchBar'
import { useDebouncedValue } from './lib/useDebounce'
import { useAppStore } from './store/useAppStore'

// The map pulls in deck.gl and maplibre; load it after the shell paints.
const MapView = lazy(() =>
  import('./components/MapView').then((module) => ({ default: module.MapView })),
)

export function App() {
  const selected = useAppStore((state) => state.selected)
  const layer = useAppStore((state) => state.layer)
  const filters = useAppStore((state) => state.filters)
  const sheet = useAppStore((state) => state.sheet)
  const filtersOpen = useAppStore((state) => state.filtersOpen)
  const select = useAppStore((state) => state.select)
  const setLayer = useAppStore((state) => state.setLayer)
  const setSheet = useAppStore((state) => state.setSheet)
  const setFiltersOpen = useAppStore((state) => state.setFiltersOpen)

  const [bbox, setBbox] = useState<Bbox | null>(null)
  const debouncedBbox = useDebouncedValue(bbox, 400)

  const score = useScore(selected)
  const chargers = useChargers(debouncedBbox, filters, true)
  const bestSites = useBestSites(layer === 'best-sites')
  const grid = useGrid(layer === 'heat')

  const chargerData = chargers.data ?? []

  return (
    <main className="relative h-full w-full overflow-hidden bg-basalt-900">
      <h1 className="sr-only">DesertCharge: find charging deserts in the US Desert Southwest</h1>
      <Suspense fallback={<div className="absolute inset-0 bg-basalt-900" />}>
        <MapView
          selected={selected}
          chargers={chargerData}
          bestSites={bestSites.data ?? []}
          grid={grid.data ?? []}
          layer={layer}
          onSelect={(lat, lng) => select({ lat, lng })}
          onBboxChange={setBbox}
        />
      </Suspense>

      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex flex-col items-center gap-3 p-4 pt-[max(1rem,env(safe-area-inset-top))]">
        <div className="pointer-events-auto w-full max-w-md">
          <SearchBar />
        </div>
        <div className="pointer-events-auto">
          <LayerToggle value={layer} onChange={setLayer} />
        </div>
      </div>

      {layer === 'heat' && (
        <div className="pointer-events-none absolute bottom-6 left-4 z-10">
          <div className="pointer-events-auto">
            <Legend />
          </div>
        </div>
      )}

      <div className="absolute inset-x-0 bottom-0 z-20 mx-auto max-w-md">
        {filtersOpen ? (
          <BottomSheet>
            <FilterSheet />
          </BottomSheet>
        ) : selected ? (
          <BottomSheet
            expandable
            expanded={sheet === 'expanded'}
            onToggle={() => setSheet(sheet === 'expanded' ? 'peek' : 'expanded')}
          >
            {score.isLoading ? (
              <p className="py-8 text-center font-mono text-sm text-bone-100/70">
                Scoring this area...
              </p>
            ) : score.data ? (
              <ScorePanel
                score={score.data}
                point={selected}
                chargers={chargerData}
                expanded={sheet === 'expanded'}
              />
            ) : (
              <p className="py-8 text-center text-sm text-bone-100/70">
                No scored data near here. Try a place inside the Desert Southwest.
              </p>
            )}
            <div className="mt-3 flex justify-center">
              <button
                type="button"
                onClick={() => setFiltersOpen(true)}
                className="font-mono text-xs uppercase tracking-[0.14em] text-brass-400"
              >
                Filters
              </button>
            </div>
          </BottomSheet>
        ) : (
          <BottomSheet>
            <p className="py-6 text-center text-[15px] text-bone-100/80">
              Search a place or tap the map to see its charging desert score.
            </p>
          </BottomSheet>
        )}
      </div>
    </main>
  )
}
