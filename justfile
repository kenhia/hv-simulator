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

# Build the image locally on this machine.
build:
    docker build -t {{image}} .

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

# Run the local validation gate (tests + lint + format check).
check:
    uv run pytest
    uv run ruff check .
    uv run ruff format --check .
