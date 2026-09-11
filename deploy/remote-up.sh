#!/usr/bin/env bash
# Bring the hvsim stack up on the deploy host from a registry image.
#
# Runs *on the host* — the justfile scps it next to compose.yaml and invokes it
# over ssh with bash explicitly, because the host's login shell is fish, which
# mis-parses the `$()` this needs.
#
#   remote-up.sh <image-ref> [expected-revision]
#
# Pins the exact image into the compose project's .env, so a later plain
# `docker compose up -d` on the host resolves the same build rather than drifting
# to whatever :latest has become since.
set -euo pipefail

ref=${1:?usage: remote-up.sh <image-ref> [expected-revision]}
expected=${2:-}
cd "$(dirname "$0")"

printf 'HVSIM_IMAGE=%s\n' "$ref" > .env
docker compose pull
docker compose up -d

# `docker compose pull` prints the same thing whether it fetched a new image or
# matched a cached one, so its output is not evidence that the requested build is
# what is running. These are. They catch a pull that silently did nothing, a
# :latest that never moved, and a compose `up` that adopted an existing container.
actual_ref=$(docker inspect hvsim --format '{{.Config.Image}}')
if [ "$actual_ref" != "$ref" ]; then
    echo "IMAGE MISMATCH: running ${actual_ref:-<none>}, asked for $ref" >&2
    exit 1
fi

# The revision label is the tighter check, and a deploy knows what it built. A
# rollback deliberately runs a commit that is not the one checked out, so it omits
# this and relies on the image reference above.
if [ -n "$expected" ]; then
    actual=$(docker inspect hvsim \
        --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')
    if [ "$actual" != "$expected" ]; then
        echo "REVISION MISMATCH: running ${actual:-<none>}, built $expected" >&2
        exit 1
    fi
fi
echo ">> running $ref${expected:+ (revision $expected)}"
