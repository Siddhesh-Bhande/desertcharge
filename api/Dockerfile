FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.11.26
WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

# Then the application.
COPY . .
RUN uv sync --no-dev --frozen

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "desertcharge.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
