-- Universe artifact — compiled SQLite schema (CONTRACT v0.1.1)
-- v0.1.1: wormhole_links.to_system_id is nullable (canon termini to unidentified systems).
--
-- The read-only artifact the engine loads. Produced by the universe-compiler
-- (Phase 2a) from the authored JSON in data/: validate -> resolve FKs ->
-- namespace ids -> write this. The engine never reads loose JSON.
--
-- Conventions:
--   * ids for bodies/places are SYSTEM-NAMESPACED ("manticore:titan") to avoid
--     cross-system collisions (Sol's Titan vs Manticore-B VI "Titan").
--   * canon: 1 = established in the source material; 0 = invented/derived by us.
--   * *_determined: 1 once an invented value is filled (else its columns are NULL).
--   * valid_from_pd / valid_to_pd: Post-Diaspora existence window (NULL = always);
--     enforced only when ALLOW_ANACHRONISMS is false.
--   * distances: AU for in-system, light-years (ly) interstellar, light-minutes
--     (lmin) for binary separations & hyper limits. Angles in degrees.

PRAGMA foreign_keys = ON;

CREATE TABLE schema_meta (
    version TEXT NOT NULL          -- contract version, e.g. "0.1.0"
);

CREATE TABLE nations (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    government        TEXT,
    capital_system_id TEXT,        -- FK star_systems.id (may be unbuilt yet)
    capital_planet    TEXT,
    capital_city      TEXT,
    founded_pd        INTEGER,
    succeeded_by      TEXT,
    canon             INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE star_systems (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    star_nation_id  TEXT REFERENCES nations(id),
    canon           INTEGER NOT NULL DEFAULT 1,
    distance_ly     REAL,          -- from Sol (canon where known)
    -- Fabricated galactic frame (Sol origin, +Z galactic north); canon = 0.
    coord_x_ly      REAL,
    coord_y_ly      REAL,
    coord_z_ly      REAL,
    coord_canon     INTEGER NOT NULL DEFAULT 0,
    is_binary       INTEGER NOT NULL DEFAULT 0,
    population      INTEGER,
    population_as_of_pd INTEGER
);

CREATE TABLE binaries (
    system_id                 TEXT PRIMARY KEY REFERENCES star_systems(id),
    eccentricity              REAL,
    barycenter_a_lmin         REAL,
    barycenter_b_lmin         REAL,
    separation_periastron_lmin REAL,
    separation_apastron_lmin  REAL,
    orbital_period_days       REAL,   -- usually derived (canon = 0)
    canon                     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE stars (
    id              TEXT PRIMARY KEY,
    system_id       TEXT NOT NULL REFERENCES star_systems(id),
    name            TEXT NOT NULL,
    role            TEXT,             -- primary | secondary
    spectral_type   TEXT,
    mass_solar      REAL,
    hyper_limit_lmin REAL,           -- derived from mass/class
    canon           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE bodies (
    id              TEXT PRIMARY KEY,           -- system-namespaced
    system_id       TEXT NOT NULL REFERENCES star_systems(id),
    parent_star_id  TEXT REFERENCES stars(id),  -- for planets
    parent_body_id  TEXT REFERENCES bodies(id), -- for moons
    name            TEXT NOT NULL,
    designation     TEXT,
    type            TEXT NOT NULL,              -- planet | moon | dwarf_planet
    subtype         TEXT,
    habitable       INTEGER NOT NULL DEFAULT 0,
    capital         INTEGER NOT NULL DEFAULT 0,
    orbit_index     INTEGER,
    canon           INTEGER NOT NULL DEFAULT 1,
    -- Keplerian elements (names mirror engine ephemeris). NULL until determined.
    orbit_canon       INTEGER NOT NULL DEFAULT 0,
    orbit_determined  INTEGER NOT NULL DEFAULT 0,
    a_au            REAL,
    e               REAL,
    i_deg           REAL,
    l_deg           REAL,
    long_peri_deg   REAL,
    long_node_deg   REAL,
    period_days     REAL,
    valid_from_pd   INTEGER,
    valid_to_pd     INTEGER
);

CREATE TABLE belts (
    id              TEXT PRIMARY KEY,
    system_id       TEXT NOT NULL REFERENCES star_systems(id),
    parent_star_id  TEXT REFERENCES stars(id),
    after_body_id   TEXT REFERENCES bodies(id),
    name            TEXT NOT NULL,
    inner_au        REAL,
    outer_au        REAL,
    canon           INTEGER NOT NULL DEFAULT 1,
    determined      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE places (                            -- stations, jun:nexus, forts, shipyards
    id              TEXT PRIMARY KEY,           -- system-namespaced
    system_id       TEXT NOT NULL REFERENCES star_systems(id),
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,
    rides_on_body_id TEXT REFERENCES bodies(id), -- = engine Station(parent=...)
    parent_star_id  TEXT REFERENCES stars(id),
    status          TEXT,                        -- active | destroyed | under_construction
    canon           INTEGER NOT NULL DEFAULT 1,
    valid_from_pd   INTEGER,
    valid_to_pd     INTEGER,
    source          TEXT
);

CREATE TABLE wormhole_junctions (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    host_system_id  TEXT REFERENCES star_systems(id),
    canon           INTEGER NOT NULL DEFAULT 1
);

-- Directed-or-undirected wormhole edges between systems (one per traversable link).
CREATE TABLE wormhole_links (
    id              TEXT PRIMARY KEY,
    junction_id     TEXT REFERENCES wormhole_junctions(id),
    from_system_id  TEXT NOT NULL REFERENCES star_systems(id),
    to_system_id    TEXT REFERENCES star_systems(id),  -- nullable: terminus to an as-yet-unidentified system
    to_terminus_name TEXT,
    distance_ly     REAL,            -- separation the link spans (lore)
    transit         TEXT,            -- "instant"
    discovered_pd   INTEGER,
    canon           INTEGER NOT NULL DEFAULT 1
);

-- Junction queue / transit-timing model (fabricated; see data/wormholes).
-- destabilization_seconds = coeff_a*sqrt(M) + coeff_b*M^2  (M = tons transited).
CREATE TABLE transit_model (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    formula          TEXT NOT NULL,
    coeff_a          REAL NOT NULL,
    coeff_b          REAL NOT NULL,
    buffer_normal_s    REAL NOT NULL,
    buffer_emergency_s REAL NOT NULL,
    canon            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE hyperspace_bands (
    band_order          INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    greek               TEXT,
    entry_velocity_limit_c REAL,
    apparent_velocity_c REAL,
    apparent_canon      INTEGER NOT NULL DEFAULT 0,
    canon               INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE hyper_limits (             -- by spectral class
    spectral_class  TEXT PRIMARY KEY,   -- e.g. "G0", "F6", "K4"
    limit_lmin      REAL NOT NULL,
    canon           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE ship_classes (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    ship_type       TEXT,
    hull_classification TEXT,
    navy            TEXT,
    affiliation_nation_id TEXT REFERENCES nations(id),
    date_introduced_pd  INTEGER,        -- = valid_from_pd for anachronism checks
    normal_g        REAL,               -- cruise accel (compensator margin)
    max_g           REAL,               -- emergency accel -> engine max_accel_g
    mass_tons       REAL,
    length_m        REAL,
    crew_total      INTEGER,
    missile_pods    INTEGER,
    canon           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE ships (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    prefix          TEXT,
    hull_number     TEXT,
    class_id        TEXT REFERENCES ship_classes(id),
    navy            TEXT,
    affiliation_nation_id TEXT REFERENCES nations(id),
    role            TEXT,
    status          TEXT,
    fate_pd         INTEGER,            -- = valid_to_pd for anachronism checks
    canon           INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_bodies_system   ON bodies(system_id);
CREATE INDEX idx_places_system   ON places(system_id);
CREATE INDEX idx_links_from      ON wormhole_links(from_system_id);
CREATE INDEX idx_links_to        ON wormhole_links(to_system_id);
CREATE INDEX idx_classes_nation  ON ship_classes(affiliation_nation_id);
