# Honorverse Simulator — deploy & ops recipes.
# `just` is a command runner (https://just.systems). Run `just` to list recipes.

set shell := ["bash", "-cu"]
set dotenv-load := true   # load .env if present (copy .env.example -> .env)

# Deploy target + port come from .env (HVSIM_HOST / HVSIM_PORT), defaulting to
# the maintainer's homelab. Override per-machine in .env, not by editing here.
host := env_var_or_default("HVSIM_HOST", "kubsdb")
port := env_var_or_default("HVSIM_PORT", "4667")
# Client-side base URL: the host publishes via tailscale serve, so plaintext
# http://<host>:<port> no longer answers from tailnet machines.
base_url := env_var_or_default("HVSIM_URL", "https://" + host + ".encke-wahoo.ts.net:" + port)
image := "hvsim:latest"     # local build tag; the registry refs are derived per build
remote_dir := "hvsim"     # ~/hvsim on the host holds the deploy compose
# Images travel through the homelab docker registry (k-homelab docs/deploying.md):
# this machine pushes, the deploy host pulls. TLS comes from `tailscale serve`, so
# there is nothing to log in to and no insecure-registries entry to distribute.
registry := env_var_or_default("HVSIM_REGISTRY", "kubsdb.encke-wahoo.ts.net:5000")

# Show available recipes.
default:
    @just --list

# Build the image locally on this machine (context = engine/). Compiles a fresh
# universe artifact and stages it into the build context (engine/universe.db,
# gitignored) so the galaxy ships inside the image.
build:
    just compile-data
    docker build -f engine/Dockerfile -t {{image}} \
        --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" .

# Build, push through the registry, and bring the stack up on {{host}} (real time).
deploy: build
    #!/usr/bin/env bash
    set -euo pipefail
    # Replaces `docker save | ssh docker load` (kwi #58, #1018). The registry is the
    # rollback history: every build stays addressable by its commit long after
    # :latest moves on, and rides the nightly /datastore backup -- where the old
    # path left history as a property of one host's local image store.
    #
    # The version is the 12-char git short SHA. The package version is a flat 0.1.0
    # that is not maintained per release, so a semver tag would collide on every
    # build and name nothing; the commit is hvsim's real version.
    rev=$(git rev-parse HEAD)
    if [ -n "$(git status --porcelain)" ]; then
        echo "!! working tree is dirty: the image would be labelled $rev without being it." >&2
        echo "   Commit first -- a build nothing can name is one nothing can roll back." >&2
        exit 1
    fi
    ref="{{registry}}/hvsim:${rev:0:12}"
    docker tag {{image}} "$ref"
    docker tag {{image}} "{{registry}}/hvsim:latest"
    # SHA first. If the :latest push then fails, the registry still holds a complete,
    # named build and :latest still points at the last good one -- the safe half-state.
    # The reverse order leaves :latest naming a build with no durable name.
    echo ">> pushing $ref …"
    docker push "$ref"
    docker push "{{registry}}/hvsim:latest"
    ssh {{host}} mkdir -p {{remote_dir}}
    scp deploy/compose.yaml deploy/remote-up.sh {{host}}:{{remote_dir}}/
    ssh {{host}} bash {{remote_dir}}/remote-up.sh "$ref" "$rev"
    echo ">> waiting for health…" && sleep 3
    just health

# Roll back to any build still in the registry: `just rollback 1a2b3c4d5e6f`.
rollback tag:
    #!/usr/bin/env bash
    set -euo pipefail
    # Pins that image on the host without building anything. `just image-tags` lists
    # the candidates; deploying again moves it forward. No revision is passed: a
    # rollback runs a commit that is deliberately not the one checked out, so
    # remote-up.sh checks the image reference instead.
    ref="{{registry}}/hvsim:{{tag}}"
    ssh {{host}} mkdir -p {{remote_dir}}
    scp deploy/compose.yaml deploy/remote-up.sh {{host}}:{{remote_dir}}/
    ssh {{host}} bash {{remote_dir}}/remote-up.sh "$ref"
    just health

# List the builds in the registry — the rollback candidates.
image-tags:
    @curl -fsS https://{{registry}}/v2/hvsim/tags/list | python3 -m json.tool

# Check the deployed service (health + clock) from this machine.
health:
    @printf 'health: '; curl -fsS {{base_url}}/health; echo
    @printf 'clock:  '; curl -fsS {{base_url}}/clock; echo

# Tail the deployed service logs (Ctrl-C to stop).
logs:
    ssh {{host}} 'cd {{remote_dir}} && docker compose logs -f'

# Stop and remove the deployed stack (the SQLite volume is preserved).
down:
    ssh {{host}} 'cd {{remote_dir}} && docker compose down'

# File a few experimental (XSS) demo ships on the deployed instance (used by M7).
seed:
    ./deploy/seed.sh {{base_url}}

# List the fleet as a text roster (ships + current plan state). Stopgap for the
# map's label crowding (kwi #57); "routes" will join this once kwi #59 lands.
fleet:
    ./deploy/fleet.sh {{base_url}}

# File repeating couriers so the galaxy runs itself (Sprint 039). Defaults to the
# deployed host; pass a base to override (e.g. http://localhost:4667).
seed-routes base=("http://" + host + ":" + port):
    python3 tools/seed-routes.py {{base}}

# Print a junction's live transit queue (the "you are #3" board). Args: [junction] [at]
queue-board junction="manticore-junction" at="":
    ./deploy/queue-board.sh {{junction}} {{base_url}} "{{at}}"

# Run the validation gate: engine (tests + lint + format), the tools, and the UI.
check:
    cd engine && uv run pytest
    cd engine && uv run ruff check .
    cd engine && uv run ruff format --check .
    cd tools/universe-compiler && uv run pytest -q
    cd tools/orbit-derive && uv run pytest -q
    cd tools/coordinate-frame && uv run pytest -q
    cd tools/nav-planner && uv run pytest -q
    python3 tools/validate-data.py data
    just ui-check

# UI dev server (Vite); proxies the API to {{base_url}}.
ui-dev:
    cd ui && HVSIM_API={{base_url}} npm run dev

# Build the galaxy SPA to ui/build (consumed by the engine + the image).
ui-build:
    cd ui && npm run build

# UI gate: types (svelte-check) + format + unit tests.
ui-check:
    cd ui && npm run check
    cd ui && npm run lint
    cd ui && npm test

# Validate the boundary contracts (build sample artifact from DDL + lint OpenAPI).
contracts:
    uv run --with openapi-spec-validator --with pyyaml python contracts/validate.py

# Fill first-pass (fabricated) orbits into data/ JSON. Commit the result.
derive-orbits:
    cd tools/orbit-derive && uv run hvsim-derive-orbits --data ../../data

# Fabricate the galactic coordinate frame into data/ JSON. Commit the result.
frame:
    cd tools/coordinate-frame && uv run hvsim-frame --data ../../data

# Validate the authored dataset (ship identity / transponder uniqueness, etc.).
validate-data:
    python3 tools/validate-data.py data

# Plan + file a fleet at a running service and print the board. Defaults to the
# deployed host (HVSIM_HOST:PORT, like `fleet`/`health`); pass a base to override
# (e.g. `just shakedown http://localhost:4667` for a local dev server). The target
# needs HVSIM_UNIVERSE_DB; the `?at=` clock sweep needs HVSIM_DEV_CLOCK=1 (403s in prod).
shakedown base=("http://" + host + ":" + port):
    cd tools/nav-planner && uv run python ../../tools/shakedown.py {{base}} ../../build/universe.db

# Markdown snapshot of the compiled artifact (seeds galaxy-changelog entries).
galaxy-summary:
    python3 tools/galaxy-summary.py build/universe.db

# Fly the canonical interstellar route (Sol -> Beowulf -> Manticore -> Grayson).
demo-route:
    cd engine && HVSIM_UNIVERSE_DB=../build/universe.db uv run demo-route

# Two couriers into the Manticore Junction: watch the transit queue count down.
queue-demo:
    cd engine && HVSIM_UNIVERSE_DB=../build/universe.db uv run queue-demo

# Plan a route for a ship (nav-planner) and show the engine's clock. Args:
# `just plan <ship> <from-system> <from-body> <to-system> <to-body>` (defaults to
# HMS Nike, Sol/earth -> Yeltsin's Star/Grayson).
plan ship="hms-nike-bc-562" fromsys="sol" frombody="earth" tosys="yeltsins-star" tobody="yeltsins-star:grayson":
    cd tools/nav-planner && uv run nav-plan --db ../../build/universe.db \
        --ship {{ship}} --from-system {{fromsys}} --from-body {{frombody}} \
        --to-system {{tosys}} --to-body {{tobody}}

# Compile data/ JSON into the read-only SQLite universe artifact (build/universe.db).
compile-data:
    cd tools/universe-compiler && uv run hvsim-compile --data ../../data \
        --schema ../../contracts/universe-artifact/schema.sql --out ../../build/universe.db
