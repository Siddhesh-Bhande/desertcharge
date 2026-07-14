# DesertCharge

Find the charging deserts in the US Desert Southwest. Search a place or use your
location and get a 0 to 100 "charging desert" score for that area, the reasons
behind it, and the nearest chargers on a map.

Status: in active development. This repository is being built in the open with a
small, incremental commit history. Live demo, screenshots, and measured metrics are
added as the milestones below land.

## The problem

Public EV charger maps tell you where chargers are. They do not tell you where
coverage is thin relative to the people who need it. DesertCharge scores any point
in the Desert Southwest (Southern California, Nevada, Arizona) by combining charger
supply with population demand, so a driver can answer a simple question: am I in a
charging desert?

The score is real spatial analysis (an H3 hex grid, nearest-neighbor distance, and
demand weighting in PostGIS), wrapped in a mobile-first consumer experience.

## Planned architecture

```
[GitHub Actions cron] --> ingest.py --> PostGIS raw:     chargers, census_tracts
                                     \-> PostGIS derived: hex_scores, best_sites
                                     \-> export:          grid.json (static CDN)

React (Vite) --> FastAPI --> PostGIS   (live: score, chargers, best-sites, route)
     |             |
  MapLibre +    OpenRouteService (routing, key server-side)
  deck.gl       Nominatim        (geocoding, proxied and cached)
```

Full design: [docs/superpowers/specs/2026-07-13-desertcharge-design.md](docs/superpowers/specs/2026-07-13-desertcharge-design.md).

## Tech stack

- Frontend: React, TypeScript, Vite, Tailwind, shadcn/ui, MapLibre GL (PMTiles
  basemap), deck.gl, TanStack Query.
- Backend: Python, FastAPI, PostGIS (via asyncpg or SQLAlchemy + GeoAlchemy2),
  slowapi rate limiting.
- Data: OpenChargeMap, NREL AFDC, US Census ACS. H3 hex grid scoring.
- Hosting (all free tier): Vercel (web), Fly.io (API), Supabase (PostGIS).

## Features

- Point desert score with an explainable breakdown.
- Nearby chargers on a map, with filters (speed, network, connector).
- Best-site suggestions: where a new charger would help most.
- deck.gl coverage heat layer over the H3 grid.
- Route and corridor analysis: find deserts along a drive.

## Milestones

1. Data pipeline, PostGIS schema, and scoring functions.
2. FastAPI backend and endpoints.
3. Map UI and the core loop (search, score, nearby chargers).
4. Charger filters.
5. deck.gl coverage heat layer.
6. Best-site suggestions.
7. Route and corridor analysis.
8. Accessibility, performance, CI, deployment, and this README as a case study.

## Local development

A one-command local run (Docker Compose) is added with the first backend milestone.
Copy `.env.example` to `.env` and fill in the values before running.

## License

MIT. See [LICENSE](LICENSE).
