# Honorverse Simulator — deploy & ops recipes.
# `just` is a command runner (https://just.systems). Run `just` to list recipes.

set shell := ["bash", "-cu"]
set dotenv-load := true   # load .env if present (copy .env.example -> .env)

# Deploy target + port come from .env (HVSIM_HOST / HVSIM_PORT), defaulting to
# the maintainer's homelab. Override per-machine in .env, not by editing here.
host := env_var_or_default("HVSIM_HOST", "kubsdb")
port := env_var_or_default("HVSIM_PORT", "4667")
image := "hvsim:latest"
remote_dir := "hvsim"     # ~/hvsim on the host holds the deploy compose

# Show available recipes.
default:
    @just --list

# Build the image locally on this machine (context = engine/). Compiles a fresh
# universe artifact and stages it into the build context (engine/universe.db,
# gitignored) so the galaxy ships inside the image.
build:
    just compile-data
    cp build/universe.db engine/universe.db
    docker build -t {{image}} engine
    rm -f engine/universe.db

# Build, ship the image to {{host}}, and bring the stack up (real-time clock).
deploy: build
    @echo ">> transferring {{image}} to {{host}} (docker save | ssh load)…"
    docker save {{image}} | ssh {{host}} docker load
    ssh {{host}} mkdir -p {{remote_dir}}
    scp deploy/compose.yaml {{host}}:{{remote_dir}}/compose.yaml
    ssh {{host}} 'cd {{remote_dir}} && docker compose up -d'
    @echo ">> waiting for health…" && sleep 3
    @just health

# Check the deployed service (health + clock) from this machine.
health:
    @printf 'health: '; curl -fsS http://{{host}}:{{port}}/health; echo
    @printf 'clock:  '; curl -fsS http://{{host}}:{{port}}/clock; echo

# Tail the deployed service logs (Ctrl-C to stop).
logs:
    ssh {{host}} 'cd {{remote_dir}} && docker compose logs -f'

# Stop and remove the deployed stack (the SQLite volume is preserved).
down:
    ssh {{host}} 'cd {{remote_dir}} && docker compose down'

# File a few experimental (XSS) demo ships on the deployed instance (used by M7).
seed:
    ./deploy/seed.sh http://{{host}}:{{port}}

# List the fleet as a text roster (ships + current plan state). Stopgap for the
# map's label crowding (kwi #57); "routes" will join this once kwi #59 lands.
fleet:
    ./deploy/fleet.sh http://{{host}}:{{port}}

# Print a junction's live transit queue (the "you are #3" board). Args: [junction] [at]
queue-board junction="manticore-junction" at="":
    ./deploy/queue-board.sh {{junction}} http://{{host}}:{{port}} "{{at}}"

# Run the validation gate: engine (tests + lint + format) and the tools' tests.
check:
    cd engine && uv run pytest
    cd engine && uv run ruff check .
    cd engine && uv run ruff format --check .
    cd tools/universe-compiler && uv run pytest -q
    cd tools/orbit-derive && uv run pytest -q
    cd tools/coordinate-frame && uv run pytest -q
    cd tools/nav-planner && uv run pytest -q
    python3 tools/validate-data.py data

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

# Plan + file a fleet at a running service and print the board (default localhost).
# Needs the service up with HVSIM_UNIVERSE_DB + HVSIM_DEV_CLOCK=1.
shakedown base="http://localhost:4667":
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
