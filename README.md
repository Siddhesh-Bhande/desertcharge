# DesertCharge

Find the charging deserts in the US Desert Southwest. Search a place or use your
location and get a 0 to 100 "charging desert" score for that area, the reasons behind
it, and the nearest chargers on a map.

The score is real spatial analysis (an H3 hex grid, nearest-neighbor distance, and
population-weighted demand in PostGIS) wrapped in a mobile-first consumer app.

Status: the full stack is built and validated on real data. Live cloud deploy is
pending free-tier accounts (Fly.io, Supabase, Vercel); it runs end to end locally
today.

## The problem

Public EV charger maps tell you where chargers are. They do not tell you where
coverage is thin relative to the people who need it. DesertCharge scores any point in
the Desert Southwest (Southern California, Nevada, Arizona) by combining charger
supply with population demand, so a driver can answer one question: am I in a charging
desert?

## Architecture

```
[scheduled ingest]  OpenChargeMap + NREL --> chargers        (PostGIS)
                    TIGERweb census       --> census_tracts   (PostGIS)
                    grid build            --> hex_scores, best_sites, grid.json

React (Vite) --> FastAPI --> PostGIS   (live: score, chargers, best-sites, geocode)
   |               |
 MapLibre +      Nominatim (geocoding, proxied server-side, rate limited)
 deck.gl
```

Full design and per-phase implementation plans live in
[docs/superpowers/](docs/superpowers/).

## How the score works

The region is tiled in H3 hexagons (resolution 7). For each populated hex:

- Demand is the census-tract population assigned to the hex, log-normalized (population
  is log-distributed, so linear normalization would hide small desert towns).
- Supply is the distance to the nearest DC fast charger and the weighted count of fast
  ports within 10 miles.
- `desert_score = 100 * sqrt(demand_norm) * supply_gap`, so a high score means many
  people with poor fast-charging access.

Validated on real data: Los Angeles scores 1 (served), the sparse desert corridor
scores 80 to 100, and the top "build a charger here" suggestions are real populous
gaps (for example, about 41,000 people and a 100-mile gap).

## Results (real end-to-end run)

- 3,698 chargers ingested from OpenChargeMap, deduped across sources.
- 8,485 census tracts (about 36M people) from the keyless TIGERweb API.
- 4,218 scored hexes plus 10 ranked best sites, exported to `grid.json`.
- Frontend initial load: 75 kB gzipped (the map bundle is code-split and streams in).

## Tech stack

- Frontend: React 19, TypeScript (strict), Vite, Tailwind v4, MapLibre GL, deck.gl,
  TanStack Query, Zustand.
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 (async) + GeoAlchemy2, PostGIS, h3,
  slowapi rate limiting, Alembic.
- Data: OpenChargeMap, NREL AFDC, US Census (via TIGERweb). H3 hex scoring.
- Hosting target (all free tier): Vercel (web), Fly.io (API), Supabase (PostGIS).

## Repository layout

```
api/    FastAPI backend, scoring engine, ingest pipeline, grid build
web/    React mobile-first frontend
docs/   design spec, design tokens, per-phase implementation plans
```

## Run it locally

Backend (needs Docker for a PostGIS container and free OpenChargeMap and NREL keys in
the repo-root `.env`; census needs no key):

```bash
cd api && uv sync
# in one shell: a PostGIS container reachable at DATABASE_URL, then
uv run alembic upgrade head
uv run python -m desertcharge.ingest.run          # chargers
uv run python -m desertcharge.ingest.census_run   # census
uv run python -m desertcharge.grid.run            # scores + best sites + grid.json
uv run uvicorn desertcharge.api.app:app --port 8000
```

Frontend:

```bash
cd web && npm install && npm run dev   # defaults to http://localhost:8000
```

## Quality gates

CI runs on every push and PR: repo hygiene, backend (ruff, strict mypy, pytest against
a real PostGIS container), and frontend (oxlint, prettier, strict tsc, vitest, build).
The whole history is Conventional Commits merged through protected-branch PRs.

## License

MIT. See [LICENSE](LICENSE).
