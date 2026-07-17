import { useEffect, useRef, useState } from 'react'

import { fetchGeocode } from '../api/client'
import type { GeocodeResult } from '../api/types'
import { useDebouncedValue } from '../lib/useDebounce'

interface PlaceInputProps {
  label: string
  placeholder: string
  onSelect: (place: { lat: number; lng: number; label: string }) => void
}

export function PlaceInput({ label, placeholder, onSelect }: PlaceInputProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodeResult[]>([])
  const [open, setOpen] = useState(false)
  const debounced = useDebouncedValue(query.trim(), 300)
  const skipRef = useRef('')

  useEffect(() => {
    if (debounced.length < 2 || debounced === skipRef.current) return
    let active = true
    fetchGeocode(debounced)
      .then((found) => {
        if (!active) return
        setResults(found)
        setOpen(found.length > 0)
      })
      .catch(() => active && setResults([]))
    return () => {
      active = false
    }
  }, [debounced])

  function choose(result: GeocodeResult) {
    const short = result.name.split(',')[0] ?? ''
    skipRef.current = short
    onSelect({ lat: result.lat, lng: result.lng, label: short })
    setQuery(short)
    setOpen(false)
  }

  return (
    <div className="relative">
      <label className="mb-1 block font-mono text-[10px] uppercase tracking-[0.12em] text-bone-100/50">
        {label}
      </label>
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        className="h-11 w-full rounded-xl bg-basalt-900 px-3.5 text-[15px] text-bone-100 placeholder:text-bone-100/40 ring-1 ring-bone-100/15 focus:outline-none focus:ring-2 focus:ring-brass-400"
      />
      {open && (
        <ul className="absolute left-0 right-0 top-[72px] z-20 overflow-hidden rounded-xl bg-basalt-700 shadow-xl">
          {results.map((result) => (
            <li key={`${result.lat},${result.lng},${result.name}`}>
              <button
                type="button"
                onClick={() => choose(result)}
                className="w-full truncate px-3.5 py-2.5 text-left text-sm text-bone-100 hover:bg-brass-400/10"
              >
                {result.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
