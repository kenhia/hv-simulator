# Honorverse ship simulator API + galaxy SPA. Multi-stage; build context is the
# REPO ROOT (so the Node stage can see ui/ and we can copy build/universe.db):
#   docker build -f engine/Dockerfile -t hvsim .   (see `just build`)

# --- Stage 1: build the Phase 2.5 galaxy SPA (ui/ -> /ui/build) ---------------
FROM node:22-slim AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# --- Stage 2: the Python runtime ---------------------------------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    HVSIM_DB=sqlite:////data/hvsim.db

WORKDIR /app
RUN pip install --no-cache-dir uv

# Install dependencies (and build the package) against the locked versions.
COPY engine/pyproject.toml engine/uv.lock engine/README.md ./
COPY engine/src ./src
RUN uv sync --frozen --no-dev

# Bundle the compiled universe artifact (built by `just compile-data`).
COPY build/universe.db /app/universe.db
ENV HVSIM_UNIVERSE_DB=/app/universe.db

# Bundle the built SPA; the engine serves it same-origin at /ui.
COPY --from=ui /ui/build /app/ui-build
ENV HVSIM_UI_DIST=/app/ui-build

# SQLite lives on a mounted volume so flight plans survive container restarts.
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "--factory", "hvsim.api.app:create_app", \
     "--host", "0.0.0.0", "--port", "8000"]
