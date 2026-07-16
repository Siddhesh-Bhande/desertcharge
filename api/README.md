# DesertCharge backend

Python backend: the desert-score engine, data pipeline, and API.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker (tests spin up a PostGIS container)

## Setup

```bash
cd api
uv sync
```

## Checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```
