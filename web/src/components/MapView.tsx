import { ScatterplotLayer } from '@deck.gl/layers'
import { H3HexagonLayer } from '@deck.gl/geo-layers'
import { MapboxOverlay } from '@deck.gl/mapbox'
import type { Layer } from '@deck.gl/core'
import { Map as MlMap } from 'maplibre-gl'
import type { IControl, StyleSpecification } from 'maplibre-gl'
import { useEffect, useRef } from 'react'

import type { BestSite, Bbox, Charger, HexScore } from '../api/types'
import type { MapLayer, SelectedPoint } from '../store/useAppStore'
import { colors, scoreColorRgba } from '../lib/tokens'

type Rgba = [number, number, number, number]

function rgba(hex: string, alpha: number): Rgba {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
    alpha,
  ]
}

const OUTLINE: Rgba = [18, 21, 26, 255]
const CHARGER_DC = rgba(colors.brass400, 230)
const CHARGER_L2 = rgba(colors.teal600, 220)
const BEST_SITE = rgba(colors.bone100, 235)
const SELECTED = rgba(colors.brass400, 255)

const DARK_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    carto: {
      type: 'raster',
      tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors © CARTO',
    },
  },
  layers: [
    { id: 'bg', type: 'background', paint: { 'background-color': colors.basalt900 } },
    { id: 'carto', type: 'raster', source: 'carto' },
  ],
}

const MOJAVE: [number, number] = [-116.0, 35.5]

interface MapViewProps {
  selected: SelectedPoint | null
  chargers: Charger[]
  bestSites: BestSite[]
  grid: HexScore[]
  layer: MapLayer
  onSelect: (lat: number, lng: number) => void
  onBboxChange: (bbox: Bbox) => void
}

function buildLayers(props: MapViewProps): Layer[] {
  const { layer, chargers, bestSites, grid, selected } = props
  const layers: Layer[] = []

  if (layer === 'heat') {
    layers.push(
      new H3HexagonLayer<HexScore>({
        id: 'heat',
        data: grid,
        getHexagon: (d) => d.h3,
        getFillColor: (d) => scoreColorRgba(d.score, 150),
        extruded: false,
        stroked: false,
        pickable: false,
      }),
    )
  }

  if (layer === 'chargers') {
    layers.push(
      new ScatterplotLayer<Charger>({
        id: 'chargers',
        data: chargers,
        getPosition: (d) => [d.lng, d.lat],
        getFillColor: (d) => (d.is_dc_fast ? CHARGER_DC : CHARGER_L2),
        getRadius: (d) => (d.is_dc_fast ? 5 : 4),
        radiusUnits: 'pixels',
        radiusMinPixels: 3,
        stroked: true,
        getLineColor: OUTLINE,
        lineWidthMinPixels: 1,
        pickable: true,
      }),
    )
  }

  if (layer === 'best-sites') {
    layers.push(
      new ScatterplotLayer<BestSite>({
        id: 'best-sites',
        data: bestSites,
        getPosition: (d) => [d.lng, d.lat],
        getFillColor: BEST_SITE,
        getRadius: 9,
        radiusUnits: 'pixels',
        stroked: true,
        getLineColor: OUTLINE,
        lineWidthMinPixels: 2,
        pickable: true,
      }),
    )
  }

  if (selected) {
    layers.push(
      new ScatterplotLayer<SelectedPoint>({
        id: 'selected',
        data: [selected],
        getPosition: (d) => [d.lng, d.lat],
        getFillColor: SELECTED,
        getRadius: 7,
        radiusUnits: 'pixels',
        stroked: true,
        getLineColor: OUTLINE,
        lineWidthMinPixels: 3,
      }),
    )
  }

  return layers
}

export function MapView(props: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MlMap | null>(null)
  const overlayRef = useRef<MapboxOverlay | null>(null)
  const propsRef = useRef(props)
  propsRef.current = props

  useEffect(() => {
    if (!containerRef.current) return
    const map = new MlMap({
      container: containerRef.current,
      style: DARK_STYLE,
      center: MOJAVE,
      zoom: 6,
      attributionControl: { compact: true },
    })
    mapRef.current = map

    const overlay = new MapboxOverlay({ interleaved: false, layers: [] })
    overlayRef.current = overlay
    map.addControl(overlay as unknown as IControl)

    const emitBbox = () => {
      const b = map.getBounds()
      propsRef.current.onBboxChange({
        minLat: b.getSouth(),
        minLng: b.getWest(),
        maxLat: b.getNorth(),
        maxLng: b.getEast(),
      })
    }
    map.on('load', emitBbox)
    map.on('moveend', emitBbox)
    map.on('click', (event) => {
      propsRef.current.onSelect(event.lngLat.lat, event.lngLat.lng)
    })

    return () => {
      map.remove()
      mapRef.current = null
      overlayRef.current = null
    }
  }, [])

  useEffect(() => {
    overlayRef.current?.setProps({ layers: buildLayers(props) })
    // Rebuild only when the rendered data or active layer changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.layer, props.chargers, props.bestSites, props.grid, props.selected])

  useEffect(() => {
    if (!props.selected || !mapRef.current) return
    mapRef.current.flyTo({
      center: [props.selected.lng, props.selected.lat],
      zoom: Math.max(mapRef.current.getZoom(), 9),
      speed: 1.2,
    })
  }, [props.selected])

  return <div ref={containerRef} className="absolute inset-0" aria-label="Coverage map" />
}
