"""Compile the Honorverse JSON dataset (data/) into the read-only SQLite
universe artifact (contracts/universe-artifact/schema.sql).

A clean, extensible JSON -> SQLite *projection*: load -> validate (best-effort
against the input schemas) -> resolve & namespace ids -> insert. The artifact is
a derived build output; data/ JSON stays the source of truth. Re-runnable; add
columns later (e.g. Phase 2.5 flavor) without changing this shape.

Compiles the full catalog: systems (+ coordinates, binary, stars with per-class
hyper limits), bodies, belts, places, nations, ship classes & ships, the
hyperspace bands + hyper-limit table, and the wormhole junctions/links + transit
model. Referenced-but-unbuilt systems/nations are stubbed so FKs hold.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3

CONTRACT_VERSION = "0.1.1"


def _b(v: object) -> int:
    return 1 if v else 0


def _int(v: object) -> int | None:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _ns(system_id: str, local_id: str | None) -> str | None:
    """System-namespace a local id (manticore + titan -> manticore:titan)."""
    return None if local_id is None else f"{system_id}:{local_id}"


def _validate(data_dir: pathlib.Path) -> list[str]:
    """Best-effort schema validation; returns a list of warning strings."""
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed; skipped validation"]

    schema_dir = data_dir / "schema"
    kind_schema = {
        "star_system": "star-system.schema.json",
        "star_nation": None,  # no schema file shipped; skip
        "ship_class_registry": "ship-class.schema.json",
        "ship_registry": "ship.schema.json",
    }
    warnings: list[str] = []
    for path in sorted(data_dir.rglob("*.json")):
        if path.parent.name == "schema":
            continue
        doc = json.loads(path.read_text())
        sfile = kind_schema.get(doc.get("kind", ""))
        if not sfile or not (schema_dir / sfile).exists():
            continue
        schema = json.loads((schema_dir / sfile).read_text())
        try:
            jsonschema.validate(doc, schema)
        except jsonschema.ValidationError as e:  # pragma: no cover - data-dependent
            warnings.append(f"{path.name}: {e.message}")
    return warnings


def _load_system(con: sqlite3.Connection, doc: dict, hyper_limits: dict[str, float]) -> None:
    sid = doc["id"]
    binary = doc.get("binary") or {}
    demo = doc.get("demographics") or {}
    loc = doc.get("location") or {}
    coords = doc.get("coordinates") or {}
    con.execute(
        "INSERT INTO star_systems (id,name,star_nation_id,canon,distance_ly,is_binary,"
        "population,population_as_of_pd,coord_x_ly,coord_y_ly,coord_z_ly,coord_canon) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            sid,
            doc["name"],
            doc.get("star_nation_id"),
            _b(doc.get("canon")),
            loc.get("distance_ly"),
            _b(binary),
            demo.get("total_population"),
            demo.get("as_of_pd"),
            coords.get("x_ly"),
            coords.get("y_ly"),
            coords.get("z_ly"),
            _b(coords.get("canon")),
        ),
    )
    if binary:
        con.execute(
            "INSERT INTO binaries (system_id,eccentricity,barycenter_a_lmin,"
            "barycenter_b_lmin,separation_periastron_lmin,separation_apastron_lmin,"
            "orbital_period_days,canon) VALUES (?,?,?,?,?,?,?,?)",
            (
                sid,
                binary.get("eccentricity"),
                binary.get("barycenter_distance_from_a_lmin"),
                binary.get("barycenter_distance_from_b_lmin"),
                binary.get("separation_periastron_lmin"),
                binary.get("separation_apastron_lmin"),
                binary.get("orbital_period_days"),
                _b(binary.get("canon")),
            ),
        )
    for star in doc.get("stars", []):
        st = star.get("spectral_type")
        hlim = hyper_limits.get(st) if st else None
        if hlim is None and st:  # fall back to the class's "0" subdivision (e.g. G5 -> G0)
            hlim = hyper_limits.get(st[0] + "0")
        con.execute(
            "INSERT INTO stars (id,system_id,name,role,spectral_type,mass_solar,"
            "hyper_limit_lmin,canon) VALUES (?,?,?,?,?,?,?,?)",
            (
                _ns(sid, star["id"]),
                sid,
                star["name"],
                star.get("role"),
                st,
                star.get("mass_solar"),
                hlim,
                _b(star.get("canon")),
            ),
        )
    for body in doc.get("bodies", []):
        _insert_body(con, sid, body)
    for belt in doc.get("belts", []):
        orb = belt.get("orbit") or {}
        con.execute(
            "INSERT INTO belts (id,system_id,parent_star_id,after_body_id,name,inner_au,"
            "outer_au,canon,determined) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                _ns(sid, belt["id"]),
                sid,
                _ns(sid, belt.get("parent_star")),
                _ns(sid, belt.get("after_body")),
                belt["name"],
                orb.get("inner_au"),
                orb.get("outer_au"),
                _b(belt.get("canon")),
                _b(orb.get("determined")),
            ),
        )
    for place in doc.get("places", []):
        con.execute(
            "INSERT INTO places (id,system_id,name,type,rides_on_body_id,parent_star_id,"
            "status,canon,valid_from_pd,valid_to_pd,source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                _ns(sid, place["id"]),
                sid,
                place["name"],
                place.get("type"),
                _ns(sid, place.get("rides_on")),
                _ns(sid, place.get("parent_star")),
                place.get("status"),
                _b(place.get("canon")),
                place.get("built_pd"),
                place.get("destroyed_pd"),
                place.get("source"),
            ),
        )


def _insert_body(
    con: sqlite3.Connection, sid: str, body: dict, parent_body: str | None = None
) -> None:
    orb = body.get("orbit") or {}
    con.execute(
        "INSERT INTO bodies (id,system_id,parent_star_id,parent_body_id,name,designation,"
        "type,subtype,habitable,capital,orbit_index,canon,orbit_canon,orbit_determined,"
        "a_au,e,i_deg,l_deg,long_peri_deg,long_node_deg,period_days) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _ns(sid, body["id"]),
            sid,
            None if parent_body else _ns(sid, body.get("parent_star")),
            parent_body,
            body["name"],
            body.get("designation"),
            body.get("type", "planet" if parent_body is None else "moon"),
            body.get("subtype"),
            _b(body.get("habitable")),
            _b(body.get("capital")),
            body.get("orbit_index"),
            _b(body.get("canon")),
            _b(orb.get("canon")),
            _b(orb.get("determined")),
            orb.get("a_au"),
            orb.get("e"),
            orb.get("i_deg"),
            orb.get("L_deg"),
            orb.get("long_peri_deg"),
            orb.get("long_node_deg"),
            orb.get("period_days"),
        ),
    )
    for moon in body.get("moons", []):
        if moon.get("named") is False:  # aggregate "N unnamed moons" entry
            continue
        _insert_body(con, sid, moon, parent_body=_ns(sid, body["id"]))


def _load_nation(con: sqlite3.Connection, doc: dict) -> None:
    con.execute(
        "INSERT INTO nations (id,name,government,capital_system_id,capital_planet,"
        "capital_city,founded_pd,succeeded_by,canon) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            doc["id"],
            doc["name"],
            doc.get("government"),
            doc.get("capital_system_id"),
            doc.get("capital_planet"),
            doc.get("capital_city"),
            doc.get("founded_pd"),
            doc.get("succeeded_by"),
            _b(doc.get("canon")),
        ),
    )


def _load_ship_classes(con: sqlite3.Connection, doc: dict) -> None:
    for c in doc.get("classes", []):
        acc = c.get("acceleration") or {}
        dim = c.get("dimensions") or {}
        crew = c.get("crew") or {}
        mag = c.get("magazines") or {}
        con.execute(
            "INSERT INTO ship_classes (id,name,ship_type,hull_classification,navy,"
            "affiliation_nation_id,date_introduced_pd,normal_g,max_g,mass_tons,length_m,"
            "crew_total,missile_pods,canon) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                c["id"],
                c["name"],
                c.get("ship_type"),
                c.get("hull_classification"),
                c.get("navy"),
                c.get("affiliation_nation_id"),
                _int(c.get("date_introduced_pd")),
                acc.get("normal_g"),
                acc.get("max_g"),
                dim.get("mass_tons"),
                dim.get("length_m"),
                crew.get("total"),
                mag.get("missile_pods"),
                _b(c.get("canon")),
            ),
        )


def _load_ships(con: sqlite3.Connection, doc: dict) -> None:
    for s in doc.get("ships", []):
        con.execute(
            "INSERT INTO ships (id,name,prefix,hull_number,class_id,navy,"
            "affiliation_nation_id,role,status,fate_pd,canon) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                s["id"],
                s["name"],
                s.get("prefix"),
                s.get("hull_number"),
                s.get("class_id"),
                s.get("navy"),
                s.get("affiliation_nation_id"),
                s.get("role"),
                s.get("status"),
                _int(s.get("fate_pd")),
                _b(s.get("canon")),
            ),
        )


def _load_hyperspace(con: sqlite3.Connection, doc: dict) -> dict[str, float]:
    """Load bands + the hyper-limit-by-class table. Returns the class->limit map."""
    for band in doc.get("bands", []):
        av = band.get("apparent_velocity_c") or {}
        con.execute(
            "INSERT INTO hyperspace_bands (band_order,name,greek,entry_velocity_limit_c,"
            "apparent_velocity_c,apparent_canon,canon) VALUES (?,?,?,?,?,?,?)",
            (
                band.get("order"),
                band.get("name"),
                band.get("greek"),
                band.get("entry_velocity_limit_c"),
                av.get("nominal_c"),
                _b(av.get("nominal_canon")),
                _b(band.get("canon")),
            ),
        )
    hl = doc.get("hyper_limit") or {}
    table = hl.get("by_spectral_class") or {}
    canon = _b(hl.get("canon"))
    for cls, lim in table.items():
        con.execute(
            "INSERT INTO hyper_limits (spectral_class,limit_lmin,canon) VALUES (?,?,?)",
            (cls, lim, canon),
        )
    return {k: float(v) for k, v in table.items()}


def _load_wormholes(con: sqlite3.Connection, doc: dict) -> None:
    for j in doc.get("junctions", []):
        con.execute(
            "INSERT INTO wormhole_junctions (id,name,host_system_id,canon) VALUES (?,?,?,?)",
            (j["id"], j.get("name"), j.get("host_system_id"), _b(j.get("canon"))),
        )
    for link in doc.get("links", []):
        eps = link.get("endpoints") or []
        frm = eps[0].get("system_id") if eps else None
        to = eps[1].get("system_id") if len(eps) > 1 else None
        to_term = (eps[1].get("terminus") or eps[1].get("label")) if len(eps) > 1 else None
        con.execute(
            "INSERT INTO wormhole_links (id,junction_id,from_system_id,to_system_id,"
            "to_terminus_name,distance_ly,transit,canon) VALUES (?,?,?,?,?,?,?,?)",
            (
                link["id"],
                link.get("via_junction"),
                frm,
                to,
                to_term,
                link.get("distance_ly"),
                link.get("transit"),
                _b(link.get("canon")),
            ),
        )
    tm = doc.get("transit_model") or {}
    if tm:
        coeff = tm.get("coefficients") or {}
        buf = tm.get("safety_buffer") or {}
        con.execute(
            "INSERT INTO transit_model (id,formula,coeff_a,coeff_b,buffer_normal_s,"
            "buffer_emergency_s,canon) VALUES (1,?,?,?,?,?,?)",
            (
                tm.get("formula"),
                coeff.get("A"),
                coeff.get("B"),
                buf.get("normal_seconds"),
                buf.get("emergency_seconds"),
                _b(tm.get("canon")),
            ),
        )


def _stub_missing_refs(con: sqlite3.Connection) -> dict[str, int]:
    """Insert placeholder rows for nations/systems referenced but not yet built.

    The dataset references systems/nations that don't have files yet (e.g. Grayson's
    `protectorate-of-grayson`, terminus systems). Stubbing keeps the real foreign
    keys intact; a later build with those files fills them in. Returns stub counts.
    """
    have_nations = {r[0] for r in con.execute("SELECT id FROM nations")}
    have_systems = {r[0] for r in con.execute("SELECT id FROM star_systems")}

    ref_nations: set[str] = set()
    for q in (
        "SELECT star_nation_id FROM star_systems",
        "SELECT affiliation_nation_id FROM ship_classes",
        "SELECT affiliation_nation_id FROM ships",
        "SELECT succeeded_by FROM nations",
    ):
        ref_nations |= {r[0] for r in con.execute(q) if r[0]}
    ref_systems: set[str] = set()
    for q in (
        "SELECT capital_system_id FROM nations",
        "SELECT host_system_id FROM wormhole_junctions",
        "SELECT from_system_id FROM wormhole_links",
        "SELECT to_system_id FROM wormhole_links",
    ):
        ref_systems |= {r[0] for r in con.execute(q) if r[0]}

    stub_n = ref_nations - have_nations
    stub_s = ref_systems - have_systems
    for nid in sorted(stub_n):
        con.execute("INSERT INTO nations (id,name,canon) VALUES (?,?,1)", (nid, nid))
    for sid in sorted(stub_s):
        con.execute(
            "INSERT INTO star_systems (id,name,canon,is_binary) VALUES (?,?,1,0)", (sid, sid)
        )
    return {"nations": len(stub_n), "systems": len(stub_s)}


def compile_universe(data_dir: pathlib.Path, schema_sql: pathlib.Path, out: pathlib.Path) -> dict:
    """Build the artifact at `out`. Returns a small summary dict."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    con = sqlite3.connect(out)
    con.executescript(schema_sql.read_text())  # creates tables (own transaction)
    con.execute("PRAGMA foreign_keys = ON")

    # One deferred transaction: order/circular refs (systems<->nations) are fine
    # as long as everything is consistent by COMMIT.
    con.execute("BEGIN")
    con.execute("PRAGMA defer_foreign_keys = ON")
    con.execute("INSERT INTO schema_meta (version) VALUES (?)", (CONTRACT_VERSION,))
    # Hyperspace first: it yields the class->hyper-limit map used to set per-star limits.
    hyper_limits: dict[str, float] = {}
    if (hf := data_dir / "hyperspace" / "hyperspace.json").exists():
        hyper_limits = _load_hyperspace(con, json.loads(hf.read_text()))
    for path in sorted((data_dir / "systems").glob("*.json")):
        _load_system(con, json.loads(path.read_text()), hyper_limits)
    for path in sorted((data_dir / "nations").glob("*.json")):
        _load_nation(con, json.loads(path.read_text()))
    if (cf := data_dir / "ships" / "ship-classes.json").exists():
        _load_ship_classes(con, json.loads(cf.read_text()))
    if (sf := data_dir / "ships" / "ships.json").exists():
        _load_ships(con, json.loads(sf.read_text()))
    if (wf := data_dir / "wormholes" / "wormhole-network.json").exists():
        _load_wormholes(con, json.loads(wf.read_text()))
    stubs = _stub_missing_refs(con)
    con.commit()

    print(f"  stubbed {stubs['nations']} unbuilt nations, {stubs['systems']} unbuilt systems")
    counts = {
        t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        for t in (
            "star_systems",
            "stars",
            "bodies",
            "belts",
            "places",
            "nations",
            "ship_classes",
            "ships",
            "hyperspace_bands",
            "hyper_limits",
            "wormhole_junctions",
            "wormhole_links",
        )
    }
    con.close()
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hvsim-compile")
    parser.add_argument("--data", required=True)
    parser.add_argument("--schema", required=True, help="contracts/universe-artifact/schema.sql")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    data_dir = pathlib.Path(args.data)
    for w in _validate(data_dir):
        print(f"  warning: {w}")
    counts = compile_universe(data_dir, pathlib.Path(args.schema), pathlib.Path(args.out))
    print(f"compiled {args.out} (contract {CONTRACT_VERSION}):")
    for table, n in counts.items():
        print(f"  {table:14} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
