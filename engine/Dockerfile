# Honorverse ship simulator API.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    HVSIM_DB=sqlite:////data/hvsim.db

WORKDIR /app
RUN pip install --no-cache-dir uv

# Install dependencies (and build the package) against the locked versions.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Bundle the compiled universe artifact (copied into the build context by
# `just build` from build/universe.db). Read-only; the engine loads it via
# HVSIM_UNIVERSE_DB to resolve systems/ships/routes.
COPY universe.db /app/universe.db
ENV HVSIM_UNIVERSE_DB=/app/universe.db

# SQLite lives on a mounted volume so flight plans survive container restarts.
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "--factory", "hvsim.api.app:create_app", \
     "--host", "0.0.0.0", "--port", "8000"]
