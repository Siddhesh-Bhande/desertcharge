import { lazy, Suspense, useState } from 'react'

import { useBestSites, useChargers, useGrid, useScore } from './api/hooks'
import type { Bbox } from './api/types'
import { BottomSheet } from './components/BottomSheet'
import { FilterSheet } from './components/FilterSheet'
import { LayerToggle } from './components/LayerToggle'
import { Legend } from './components/Legend'
import { RoutePanel } from './components/RoutePanel'
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
  const routeOpen = useAppStore((state) => state.routeOpen)
  const route = useAppStore((state) => state.route)
  const mapTheme = useAppStore((state) => state.mapTheme)
  const select = useAppStore((state) => state.select)
  const setLayer = useAppStore((state) => state.setLayer)
  const setSheet = useAppStore((state) => state.setSheet)
  const setFiltersOpen = useAppStore((state) => state.setFiltersOpen)
  const setRouteOpen = useAppStore((state) => state.setRouteOpen)
  const toggleMapTheme = useAppStore((state) => state.toggleMapTheme)

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
          route={route}
          layer={layer}
          theme={mapTheme}
          onSelect={(lat, lng) => select({ lat, lng })}
          onBboxChange={setBbox}
        />
      </Suspense>

      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex flex-col items-center gap-3 p-4 pt-[max(1rem,env(safe-area-inset-top))]">
        <div className="pointer-events-auto w-full max-w-md">
          <SearchBar />
        </div>
        <div className="pointer-events-auto flex items-center gap-2">
          <LayerToggle value={layer} onChange={setLayer} />
          <button
            type="button"
            onClick={() => setRouteOpen(true)}
            aria-pressed={routeOpen}
            className="rounded-full bg-basalt-800/95 px-3.5 py-2 text-xs font-semibold text-bone-100/80 shadow-lg backdrop-blur hover:text-bone-100"
          >
            Route
          </button>
          <button
            type="button"
            onClick={toggleMapTheme}
            aria-label={mapTheme === 'dark' ? 'Switch to light map' : 'Switch to dark map'}
            className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-basalt-800/95 text-bone-100/80 shadow-lg backdrop-blur hover:text-bone-100"
          >
            {mapTheme === 'dark' ? (
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden
              >
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 1.4M6.4 17.6 5 19" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
              </svg>
            )}
          </button>
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
        {routeOpen ? (
          <BottomSheet>
            <RoutePanel />
          </BottomSheet>
        ) : filtersOpen ? (
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
