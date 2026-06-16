"""universe — load the compiled SQLite universe artifact and place bodies.

Read-only access to the artifact (built by the universe-compiler from data/), plus
binary-aware positions: a system's frame is centred on its barycenter; binary
stars orbit it (mass-ratio split of a Keplerian relative orbit); planets orbit
their parent star; moons their parent body. All pure functions over the artifact;
Sol is handled separately by the JPL ephemeris (see resolve_position).
"""

from __future__ import annotations

import math
import sqlite3
from datetime import datetime

from hvsim.ephemeris import heliocentric_position
from hvsim.ephemeris.kepler import AU_M, _orbital_to_xyz, days_since_j2000
from hvsim.kinematics import Vec3

LMIN_M = 1.798754748e10  # 1 light-minute in metres
LY_M = 9.460730472580800e15  # 1 light-year in metres


class Universe:
    """Read-only handle to a compiled universe artifact."""

    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con
        self.con.row_factory = sqlite3.Row

    @classmethod
    def open(cls, path: str) -> Universe:
        # check_same_thread=False: read-only, shared across FastAPI's threadpool.
        return cls(sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False))

    def systems(self) -> list[dict]:
        return [dict(r) for r in self.con.execute("SELECT * FROM star_systems ORDER BY id")]

    def system(self, system_id: str) -> dict | None:
        r = self.con.execute("SELECT * FROM star_systems WHERE id=?", (system_id,)).fetchone()
        return dict(r) if r else None

    def stars(self, system_id: str) -> list[dict]:
        return [
            dict(r) for r in self.con.execute("SELECT * FROM stars WHERE system_id=?", (system_id,))
        ]

    def binary(self, system_id: str) -> dict | None:
        r = self.con.execute("SELECT * FROM binaries WHERE system_id=?", (system_id,)).fetchone()
        return dict(r) if r else None

    def bodies(self, system_id: str) -> list[dict]:
        return [
            dict(r)
            for r in self.con.execute("SELECT * FROM bodies WHERE system_id=?", (system_id,))
        ]

    def wormhole_junctions(self) -> list[dict]:
        return [dict(r) for r in self.con.execute("SELECT * FROM wormhole_junctions ORDER BY id")]

    def wormhole_junction(self, junction_id: str) -> dict | None:
        r = self.con.execute(
            "SELECT * FROM wormhole_junctions WHERE id=?", (junction_id,)
        ).fetchone()
        return dict(r) if r else None

    def wormhole_links(self) -> list[dict]:
        return [dict(r) for r in self.con.execute("SELECT * FROM wormhole_links ORDER BY id")]

    # -- Hyperspace / wormhole model (the travel parameters, read from data) ----

    def hyperspace_bands(self) -> list[dict]:
        return [
            dict(r) for r in self.con.execute("SELECT * FROM hyperspace_bands ORDER BY band_order")
        ]

    def hyperspace_band(self, band_order: int) -> dict | None:
        r = self.con.execute(
            "SELECT * FROM hyperspace_bands WHERE band_order=?", (band_order,)
        ).fetchone()
        return dict(r) if r else None

    def transit_model(self) -> dict | None:
        r = self.con.execute("SELECT * FROM transit_model WHERE id=1").fetchone()
        return dict(r) if r else None

    def hyperspace_model(self) -> dict | None:
        r = self.con.execute("SELECT * FROM hyperspace_model WHERE id=1").fetchone()
        return dict(r) if r else None

    def ship(self, ship_id: str) -> dict | None:
        r = self.con.execute("SELECT * FROM ships WHERE id=?", (ship_id,)).fetchone()
        return dict(r) if r else None

    def ship_class(self, class_id: str) -> dict | None:
        r = self.con.execute("SELECT * FROM ship_classes WHERE id=?", (class_id,)).fetchone()
        return dict(r) if r else None

    def effective_ship(self, ship_id: str) -> dict | None:
        """A ship's effective stats = class values with ship overrides applied.

        Resolves COALESCE(ship.ovr_*, class.*) for the engine-relevant fields, so
        a hull with an upgrade/mod/damage shadows its class. Returns None if the
        ship (or its class) is missing.
        """
        s = self.ship(ship_id)
        if s is None:
            return None
        c = self.ship_class(s["class_id"]) or {}

        def eff(ovr_key: str, class_key: str):
            return s[ovr_key] if s.get(ovr_key) is not None else c.get(class_key)

        return {
            "id": s["id"],
            "name": s["name"],
            "class_id": s["class_id"],
            "transponder": s.get("transponder"),
            "modified": s.get("modified"),
            "max_g": eff("ovr_max_g", "max_g"),
            "normal_g": eff("ovr_normal_g", "normal_g"),
            "max_hyper_band": eff("ovr_max_hyper_band", "max_hyper_band"),
            "real_cruise_velocity_c": eff("ovr_real_cruise_velocity_c", "real_cruise_velocity_c"),
            "mass_tons": c.get("mass_tons"),
        }

    def transponder(self, ship_id: str) -> str | None:
        """The ship's display transponder ``nation.class.hull`` (None if unknown)."""
        s = self.ship(ship_id)
        return s.get("transponder") if s else None

    def ship_by_transponder(self, transponder: str) -> dict | None:
        """The ship squawking ``transponder`` (display ``nation.class.hull``)."""
        r = self.con.execute("SELECT * FROM ships WHERE transponder=?", (transponder,)).fetchone()
        return dict(r) if r else None

    def effective_ship_by_transponder(self, transponder: str) -> dict | None:
        """Resolve a transponder straight to its hull's effective technical data."""
        s = self.ship_by_transponder(transponder)
        return self.effective_ship(s["id"]) if s else None

    def hyper_limit_lmin(self, system_id: str) -> float | None:
        """The primary star's hyper limit (light-minutes).

        Sol is special-cased (no star row in the artifact): it is a G2 star, so
        the canon-exact G2 entry from the hyper-limit table is used.
        """
        if system_id == "sol":
            r = self.con.execute(
                "SELECT limit_lmin FROM hyper_limits WHERE spectral_class='G2'"
            ).fetchone()
            return r[0] if r else None
        r = self.con.execute(
            "SELECT hyper_limit_lmin FROM stars WHERE system_id=? "
            "ORDER BY (role='primary') DESC LIMIT 1",
            (system_id,),
        ).fetchone()
        return r[0] if r and r[0] is not None else None

    def coordinates(self, system_id: str) -> tuple[float, float, float] | None:
        """A system's galactic-frame coordinates (ly); Sol is the origin."""
        return _coords(self, system_id)

    def wormhole_link_between(self, a: str, b: str) -> dict | None:
        """The wormhole link directly connecting systems ``a`` and ``b``, if any."""
        r = self.con.execute(
            "SELECT * FROM wormhole_links "
            "WHERE (from_system_id=? AND to_system_id=?) OR (from_system_id=? AND to_system_id=?) "
            "LIMIT 1",
            (a, b, b, a),
        ).fetchone()
        return dict(r) if r else None


def format_transponder(nation: int, ship_class: int, hull: int) -> str:
    """The display transponder string ``nation.class.hull`` (modified is engine-only)."""
    return f"{nation}.{ship_class}.{hull}"


def parse_transponder(transponder: str) -> tuple[int, int, int]:
    """Parse ``nation.class.hull`` into integer components."""
    parts = transponder.split(".")
    if len(parts) != 3:
        raise ValueError(f"malformed transponder {transponder!r} (want nation.class.hull)")
    nation, ship_class, hull = (int(p) for p in parts)
    return nation, ship_class, hull


def _coords(u: Universe, system_id: str) -> tuple[float, float, float] | None:
    """A system's galactic-frame coordinates (ly). Sol is the origin."""
    if system_id == "sol":
        return (0.0, 0.0, 0.0)
    s = u.system(system_id)
    if s and s.get("coord_x_ly") is not None:
        return (s["coord_x_ly"], s["coord_y_ly"], s["coord_z_ly"])
    return None


def inter_system_distance(u: Universe, a: str, b: str) -> dict:
    """Distance (ly) between two systems: canon wormhole-link span if directly
    linked, else the frame-derived Euclidean distance. method records which."""
    row = u.con.execute(
        "SELECT distance_ly FROM wormhole_links "
        "WHERE (from_system_id=? AND to_system_id=?) OR (from_system_id=? AND to_system_id=?) "
        "LIMIT 1",
        (a, b, b, a),
    ).fetchone()
    if row and row[0] is not None:
        return {"distance_ly": row[0], "method": "wormhole-canon"}
    ca, cb = _coords(u, a), _coords(u, b)
    if ca and cb:
        d = math.sqrt(sum((x - y) ** 2 for x, y in zip(ca, cb, strict=True)))
        return {"distance_ly": round(d, 3), "method": "frame"}
    return {"distance_ly": None, "method": "unknown"}


def _kepler_offset_m(body: dict, when: datetime) -> Vec3:
    """Position of a body relative to its primary, from its orbit row (metres)."""
    period = body["period_days"] or 0.0
    n = 360.0 / period if period else 0.0
    mean_long = (body["l_deg"] or 0.0) + n * days_since_j2000(when)
    long_peri = body["long_peri_deg"] or 0.0
    mean_anom = math.radians(((mean_long - long_peri + 180.0) % 360.0) - 180.0)
    node = math.radians(body["long_node_deg"] or 0.0)
    arg_peri = math.radians(long_peri) - node
    x, y, z = _orbital_to_xyz(
        body["a_au"],
        body["e"] or 0.0,
        math.radians(body["i_deg"] or 0.0),
        arg_peri,
        node,
        mean_anom,
    )
    return Vec3(x * AU_M, y * AU_M, z * AU_M)


def star_positions(u: Universe, system_id: str, when: datetime) -> dict[str, Vec3]:
    """Star positions in the system (barycenter-centred) frame, in metres."""
    stars = u.stars(system_id)
    binb = u.binary(system_id)
    if binb and len(stars) >= 2:
        primary = next((s for s in stars if s["role"] == "primary"), stars[0])
        secondary = next((s for s in stars if s["role"] == "secondary"), stars[1])
        a_sep_m = ((binb["barycenter_a_lmin"] or 0.0) + (binb["barycenter_b_lmin"] or 0.0)) * LMIN_M
        e = binb["eccentricity"] or 0.0
        m_a = primary["mass_solar"] or 1.0
        m_b = secondary["mass_solar"] or 1.0
        m_tot = m_a + m_b
        a_sep_au = a_sep_m / AU_M
        period_days = binb["orbital_period_days"] or (365.25 * math.sqrt(a_sep_au**3 / m_tot))
        mean_anom = math.radians((360.0 / period_days * days_since_j2000(when)) % 360.0)
        rx, ry, rz = _orbital_to_xyz(a_sep_m, e, 0.0, 0.0, 0.0, mean_anom)  # A->B vector
        return {
            primary["id"]: Vec3(-rx * m_b / m_tot, -ry * m_b / m_tot, -rz * m_b / m_tot),
            secondary["id"]: Vec3(rx * m_a / m_tot, ry * m_a / m_tot, rz * m_a / m_tot),
        }
    return {s["id"]: Vec3(0.0, 0.0, 0.0) for s in stars}


def body_positions(u: Universe, system_id: str, when: datetime) -> dict[str, Vec3]:
    """All placeable bodies' positions (metres) in the system frame at `when`.

    Bodies without a determined orbit (e.g. moons this phase) are skipped.
    """
    spos = star_positions(u, system_id, when)
    out: dict[str, Vec3] = {}
    for bd in u.bodies(system_id):
        if not bd["orbit_determined"] or bd["a_au"] is None:
            continue
        offset = _kepler_offset_m(bd, when)
        if bd["parent_body_id"]:
            base = out.get(bd["parent_body_id"])
            if base is None:
                continue
        else:
            base = spos.get(bd["parent_star_id"], Vec3(0.0, 0.0, 0.0))
        out[bd["id"]] = base + offset
    return out


def resolve_position(
    u: Universe | None, system_id: str, body_id: str, when: datetime
) -> Vec3 | None:
    """System-aware position. Sol uses the JPL ephemeris; others the artifact."""
    if system_id == "sol":
        return Vec3(*heliocentric_position(body_id, when))
    if u is None:
        return None
    return body_positions(u, system_id, when).get(body_id)
