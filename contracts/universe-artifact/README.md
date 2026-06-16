# Universe artifact — contract v0.4.0

The **compiled, read-only SQLite** the engine loads to know the galaxy. It is the
seam between the data side (authored JSON in `data/`) and the engine: the
**universe-compiler** (Phase 2a) reads the JSON, validates it, resolves foreign
keys, namespaces ids, and writes a database matching [`schema.sql`](schema.sql).
The engine never reads loose JSON.

This contract is **versioned** (`schema_meta.version`) and frozen per minor
version; it will grow through Phase 2a–2c. Freezing the shape now is what keeps
the tools, the engine, and a possible future Rust engine independent.

## Why SQLite (not JSON) at runtime

- **JSON stays the source of truth** in `data/` — git-diffable, PR-reviewable,
  per-fact `canon` flags, CC BY-SA attribution.
- **SQLite is the runtime store** — relational integrity (FKs), graph queries
  (the wormhole network is naturally relational), one read-only file, zero-ops,
  already in our toolchain. "JSON gets hard to add to" never reaches the engine.

## Shape (see `schema.sql` for columns)

- **Catalog:** `nations`, `star_systems` (+ `binaries`), `stars`, `bodies`
  (planets + moons via `parent_body_id`), `belts`, `places` (stations/nexus/forts,
  `rides_on_body_id` = engine `Station(parent=...)`).
- **Network:** `wormhole_junctions` (+ `traffic_intensity`, a fabricated mean
  queue depth feeding the queue resolver), `wormhole_links` (edges),
  `transit_model` (the queue/destabilization coefficients), `hyperspace_bands`,
  `hyper_limits`.
- **Fleet:** `ship_classes` (carries `normal_g`/`max_g`), `ships`.

## Conventions

- **Id namespacing:** body/place ids are system-qualified (`manticore:titan`) so
  Sol's Titan and Manticore-B VI "Titan" don't collide.
- **`canon`** (1/0) per row; orbital geometry has its own `orbit_canon` /
  `orbit_determined` (existence can be canon while placement is invented).
- **Temporal validity:** `valid_from_pd` / `valid_to_pd` (NULL = always);
  enforced only when `ALLOW_ANACHRONISMS` is false. `ship_classes.date_introduced_pd`
  and `ships.fate_pd` feed these.
- **Units:** AU in-system, ly interstellar, light-minutes for binary separations
  and hyper limits; degrees for angles. Element names mirror the engine ephemeris.

## Validation

`just contracts` (root) builds an empty database from `schema.sql` in memory to
prove the DDL is valid, and lints the engine OpenAPI. The compiler that populates
it from `data/` arrives in Phase 2a.
