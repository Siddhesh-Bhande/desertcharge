# DesertCharge: Charging Desert Finder (Design Spec)

Date: 2026-07-13
Status: Approved design, pending user review of this spec
Portfolio flagship: #3 (GIS, spatial analysis, map UX)

## 1. Summary

DesertCharge is a mobile-first web app for the Desert Southwest (Southern
California, Nevada, Arizona). A user searches a place or uses their location and
gets a 0 to 100 "charging desert" score for that area, the plain-language reasons
behind it, and nearby chargers on a map. The consumer question is "am I in a
charging desert?" The score itself is real spatial analysis, so the app proves
GIS, PostGIS spatial queries, a data pipeline, and map UX while staying relatable.

It runs entirely on free tiers and open-source tooling. It is not the portfolio's
one AWS project.

## 2. Goals and non-goals

### Goals
- Prove GIS and spatial analysis: PostGIS queries, an H3 hex scoring grid, corridor
  buffering, nearest-neighbor distance.
- Prove a real data pipeline: scheduled ingest, merge, transform, derived tables.
- Prove map UX and performance: MapLibre GL base map with a deck.gl GPU heat layer
  at 60fps.
- Ship a polished mobile-first experience that embeds in an iframe and survives a
  cold start.
- Meet every gate in `rules.md`: strict types, tests in CI, WCAG 2.2 AA, Lighthouse
  95+, no secrets in the client, no gradients, no AI tells, no emdashes.

### Non-goals
- Real-time charger availability (source feeds are not reliably live).
- User accounts, payments, or reviews.
- Nationwide or global coverage.
- A native mobile app.

## 3. Users and core loop

Primary user: an EV driver or curious visitor on a phone.

Core loop:
1. Search a place (geocoded) or tap "use my location."
2. See a desert score (0 to 100) for that point, a one-line verdict, and a nearby-
   charger count in a collapsed bottom sheet.
3. Expand the sheet for the score breakdown, a nearby-charger list, and filters.
4. Optionally switch layers (chargers, coverage heat, best sites) or enter route mode.

## 4. Core UX (mobile-first)

Single map-centric screen. Full-bleed MapLibre map with a floating bottom sheet as
the primary control surface.

- Top: search and locate bar (geocode input plus a "use my location" button).
- Bottom sheet, collapsed: large desert score, a verdict such as "Underserved:
  nearest fast charger is 23 miles away," and a nearby-charger count.
- Bottom sheet, expanded: score breakdown (population served, distance to nearest
  DC fast charger, chargers within 10 miles), a scrollable nearby-charger list, and
  filter chips.
- Layer toggle: chargers (default), coverage heat (deck.gl), best sites.
- Route mode: enter a destination, draw the A to B route, highlight desert stretches
  along the corridor and the single worst gap.

Accessibility is a hard gate: full keyboard navigation for the map controls and the
sheet, managed focus, labeled controls, and `prefers-reduced-motion` respected.

## 5. Desert-score method

Tile the region in H3 hexagons at resolution 7 (roughly 5 km edge). Precompute per
hex:

- Demand: population from Census ACS, areal-weighted from tract polygons into hexes.
  Road traffic (state DOT AADT) is an optional later blend for corridors.
- Supply: distance from the hex centroid to the nearest DC fast charger, and a
  weighted count of chargers within 10 miles (weighted by power and port count).

Score (tunable, documented, validated against known deserts during implementation):

```
demand_norm    = normalize(population)                    # 0..1 across region
access         = min(1, weighted_chargers_10mi / 3)       # 0..1, higher is better
distance_gap   = clamp(nearest_dc_fast_miles / 30, 0, 1)  # 30 mi = full gap
supply_gap     = 0.5 * distance_gap + 0.5 * (1 - access)  # 0..1, higher is worse
desert_score   = round(100 * sqrt(demand_norm) * supply_gap)
```

The square root on demand lets moderately populated but underserved areas still
score meaningfully. For any queried point we return the containing hex's score plus
the two or three factors that drove it, so the number is always explainable.

Best sites: rank empty, high-demand hexes that are far from existing chargers.
Surface the top N as "a charger here would serve about X people and close a Y-mile
gap."

## 6. Architecture and data flow

```
[GitHub Actions cron] --> ingest.py --> PostGIS raw:     chargers, census_tracts
                                     \-> PostGIS derived: hex_scores, best_sites
                                     \-> export:          grid.json (static CDN)

React (Vite) --> FastAPI --> PostGIS      (live: /score, /chargers, /best-sites, /route)
     |             |
  MapLibre +    OpenRouteService (routing, key server-side, rate-limited)
  deck.gl       Nominatim        (geocoding, proxied, cached, rate-limited)
     |
  basemap.pmtiles + grid.json (static object storage / CDN)
```

Two static assets sit on the CDN. `basemap.pmtiles` is the MapLibre vector basemap
for the region (read via the pmtiles protocol, no API key). `grid.json` is a compact
array of `{ h3, score }` records that the deck.gl H3HexagonLayer consumes for the
heat layer. Both are static so the map is never blank on a cold backend, and live
endpoints handle arbitrary-point scoring, nearby chargers, filters, and route
corridors.

## 7. Data model (PostGIS)

- `chargers` (id, source, source_id, name, geom Point 4326, power_kw,
  connector_types text[], network, num_ports, is_dc_fast bool, last_seen)
- `census_tracts` (geoid, state, geom MultiPolygon 4326, population, households)
- `hex_scores` (h3_index pk, geom Polygon, centroid Point, population,
  nearest_dc_fast_m, weighted_chargers_10mi, desert_score, updated_at)
- `best_sites` (id pk, h3_index, geom Point, rank, est_population_served,
  gap_miles_closed, reason)

Spatial indexes (GiST) on all geometry columns.

## 8. API (FastAPI, typed, rate-limited)

- `GET  /api/health` - liveness for the keep-warm ping.
- `GET  /api/score?lat&lng` - `{ score, verdict, factors, hex_index }`.
- `GET  /api/chargers?bbox&speed&network&connector` - GeoJSON FeatureCollection.
- `GET  /api/best-sites?bbox&limit` - ranked list.
- `POST /api/route` - body `{ origin, destination }` returns route GeoJSON, corridor
  desert hexes, the worst gap, and chargers along the corridor.
- `GET  /api/geocode?q` - proxied Nominatim results (cached server-side).
- Static (not FastAPI): `basemap.pmtiles` for MapLibre and `grid.json` for the
  deck.gl heat layer, both served from the CDN.

All keys (OpenChargeMap, NREL, OpenRouteService) live server-side only. `slowapi`
enforces per-IP limits on every endpoint that hits a third-party API so a demo
cannot run up a bill.

## 9. Data pipeline (`ingest.py`)

Idempotent, logged, and run weekly by GitHub Actions (the run also keeps the backend
warm). Steps:

1. Fetch chargers from the OpenChargeMap API (region bbox) and cross-reference NREL
   AFDC EV stations. Merge and dedupe.
2. Fetch Census ACS tract population and TIGER/Line tract geometries for CA, NV, AZ.
3. Load raw tables into PostGIS.
4. Build the H3 res-7 grid over the region bbox.
5. Areal-weight tract population into hexes.
6. Compute nearest DC fast distance and weighted charger count per hex via PostGIS
   (KNN and `ST_DWithin`).
7. Compute `desert_score` per hex.
8. Rank `best_sites`.
9. Export the heat-layer grid to `grid.json`, filtered to hexes with population above
   a small threshold (unpopulated desert scores 0 by definition, so dropping it keeps
   the payload inside the bundle budget), served gzipped from the CDN. Separately,
   build `basemap.pmtiles` for the region once (it changes rarely).

Transforms (areal weighting, scoring, best-site ranking) are pure functions with
unit tests over a small fixture dataset.

## 10. Feature builds (the four extras)

- Best-site suggestions: precomputed ranking rendered as distinct markers with a
  "why here" popover.
- deck.gl heat layer: H3HexagonLayer over the precomputed grid, targeting 60fps,
  with a measured FPS note in the README.
- Route/corridor analysis: OpenRouteService returns the route; PostGIS buffers the
  line and finds desert hexes and chargers within the corridor; the UI highlights
  the worst gap.
- Charger filters: fast/slow, network, connector type as live PostGIS `WHERE`
  clauses on `/api/chargers`.

## 11. Tech stack (open source, free-tier)

- Frontend: React + TypeScript + Vite, Tailwind + shadcn/ui (components structured so
  they can later be extracted into `bhande/ui`, which is project #6 and does not yet
  exist), MapLibre GL with a self-hosted PMTiles vector basemap of the region (no API
  key, no per-tile rate limit), deck.gl for the heat layer, TanStack Query.
- Backend: Python FastAPI, Pydantic, async PostGIS access (asyncpg or SQLAlchemy +
  GeoAlchemy2), `slowapi` rate limiting.
- Database: Postgres + PostGIS on Supabase free tier (PostGIS preinstalled).
- Routing: OpenRouteService hosted API (free tier, server-side key).
- Geocoding: hosted Nominatim proxied through the backend with caching.

## 12. Deployment, free tier, cold-start

- Frontend on Vercel. Backend (FastAPI in Docker) on Fly.io. Database on Supabase.
  Static grid on object storage or the frontend CDN.
- Cold-start plan (a P0 in `rules.md`): the heat-layer grid is static so the map is
  never blank; a GitHub Actions cron pings `/api/health` to keep the backend warm;
  the score endpoint shows a "waking the demo" state on first hit.
- Iframe-embeddable, with appropriate headers.
- This project stays fully free. It is not the portfolio's one AWS project.

## 13. Testing and quality gates

- Strict TypeScript (no `any`), typed Python (mypy, ruff), ESLint and Prettier.
- Backend: pytest on scoring logic, PostGIS queries against a seeded test database,
  FastAPI endpoint tests, and edge cases (point outside region, no chargers nearby,
  invalid coordinates).
- Frontend: Vitest and React Testing Library, a Playwright test for the core flow
  (search, score, map), axe-core in CI.
- GitHub Actions runs install, typecheck, lint, test, and build on every push and PR,
  with a bundle-size budget that fails CI when exceeded and a status badge in the
  README.
- WCAG 2.2 AA verified; Lighthouse 95+; LCP <= 2.5s, INP <= 200ms, CLS <= 0.1.

## 14. Security

- No secrets in the repo or the client bundle. All third-party keys are held by the
  backend.
- Every public endpoint that hits a paid or rate-limited third-party API is rate
  limited per IP.
- `.env.example` present; real values only in deployment secrets.

## 15. Repository and conventions

- Lives in `PortfolioProjects/desertcharge/` as its own repo with README (case
  study), LICENSE (MIT), `.gitignore`, `.env.example`, and CI workflow.
- Conventional Commits, small incremental history, PR-based merges.
- Files kept under about 300 lines; conventional folder layout.
- No emdashes anywhere; plain, specific copy; no gradients or AI tells.

## 16. Milestones (for the implementation plan to expand)

1. Data pipeline plus PostGIS schema plus scoring functions (with fixture tests).
2. FastAPI backend and endpoints.
3. Map UI and the core loop (search, score, nearby chargers).
4. Charger filters.
5. deck.gl coverage heat layer.
6. Best-site suggestions.
7. Route and corridor analysis.
8. Accessibility, performance, CI, deployment, and the case-study README.

## 17. Resolved decisions

- Framing: consumer "am I in a charging desert?" with real spatial analysis beneath.
- Region: Desert Southwest corridor (SoCal, Nevada, Arizona).
- Scope: core loop plus all four extras (best sites, heat layer, route corridor,
  filters).
- Architecture: hybrid (scheduled precompute plus live PostGIS at request time).
- Hosting: fully free (Vercel, Fly.io, Supabase); not the AWS project.
- Basemap: MapLibre GL plus self-hosted PMTiles.
- Working name: DesertCharge.
