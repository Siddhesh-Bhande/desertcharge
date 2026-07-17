import { useState } from 'react'

import { fetchGeocode } from '../api/client'
import type { GeocodeResult } from '../api/types'
import { useAppStore } from '../store/useAppStore'

export function SearchBar() {
  const select = useAppStore((state) => state.select)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodeResult[]>([])
  const [open, setOpen] = useState(false)
  const [locating, setLocating] = useState(false)

  async function runSearch(value: string) {
    setQuery(value)
    if (value.trim().length < 2) {
      setResults([])
      setOpen(false)
      return
    }
    try {
      const found = await fetchGeocode(value.trim())
      setResults(found)
      setOpen(found.length > 0)
    } catch {
      setResults([])
      setOpen(false)
    }
  }

  function choose(result: GeocodeResult) {
    select({ lat: result.lat, lng: result.lng, label: result.name.split(',')[0] })
    setQuery(result.name.split(',')[0] ?? '')
    setOpen(false)
  }

  function locate() {
    if (!navigator.geolocation) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        select({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          label: 'Your location',
        })
        setLocating(false)
      },
      () => setLocating(false),
      { enableHighAccuracy: false, timeout: 8000 },
    )
  }

  return (
    <div className="relative">
      <div className="flex h-13 items-center gap-3 rounded-full bg-basalt-800/95 pl-4.5 pr-2 shadow-lg ring-[1.5px] ring-brass-400 backdrop-blur">
        <SearchIcon />
        <input
          type="search"
          value={query}
          onChange={(event) => void runSearch(event.target.value)}
          onFocus={() => setOpen(results.length > 0)}
          placeholder="Search a place"
          aria-label="Search a place"
          className="h-full flex-1 bg-transparent text-[15px] text-bone-100 placeholder:text-bone-100/45 focus:outline-none"
        />
        <button
          type="button"
          onClick={locate}
          aria-label="Use my location"
          aria-busy={locating}
          className="flex h-9.5 w-9.5 items-center justify-center rounded-full bg-basalt-900"
        >
          <LocateIcon spinning={locating} />
        </button>
      </div>
      {open && (
        <ul className="absolute left-0 right-0 top-15 z-10 overflow-hidden rounded-2xl bg-basalt-800/98 shadow-xl backdrop-blur">
          {results.map((result) => (
            <li key={`${result.lat},${result.lng},${result.name}`}>
              <button
                type="button"
                onClick={() => choose(result)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-brass-400/10"
              >
                <span className="flex-1 truncate text-[15px] text-bone-100">{result.name}</span>
                {result.kind && (
                  <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-bone-100/50">
                    {result.kind}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
      <circle cx="7" cy="7" r="5" fill="none" stroke="rgba(233,227,214,.5)" strokeWidth="1.5" />
      <path d="M11 11L15 15" stroke="rgba(233,227,214,.5)" strokeWidth="1.5" />
    </svg>
  )
}

function LocateIcon({ spinning }: { spinning: boolean }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      aria-hidden
      className={spinning ? 'animate-spin' : ''}
    >
      <circle cx="9" cy="9" r="5" fill="none" stroke="#C9A467" strokeWidth="1.5" />
      <path d="M9 0v3M9 15v3M0 9h3M15 9h3" stroke="#C9A467" strokeWidth="1.5" />
    </svg>
  )
}
