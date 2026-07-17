# DesertCharge web

Mobile-first React app for the DesertCharge charging-desert finder. MapLibre GL base
map with a deck.gl data overlay, wired to the FastAPI backend.

## Requirements

- Node 22+
- The API running (see `../api`), or a deployed API URL.

## Setup

```bash
npm install
cp .env.example .env   # optional; defaults target http://localhost:8000
npm run dev
```

## Environment

- `VITE_API_BASE_URL` (default `http://localhost:8000`): the DesertCharge API.
- `VITE_GRID_URL` (default `/grid.json`): the static scored grid for the heat layer.

## Checks

```bash
npm run lint        # oxlint
npm run format      # prettier
npm run typecheck   # tsc
npm test            # vitest
npm run build       # tsc + vite build
```

## Stack

React 19, TypeScript (strict), Vite, Tailwind v4, MapLibre GL, deck.gl, TanStack Query,
Zustand. Design tokens come from `../docs/design/design-tokens.md`.
