"""Shared test fixtures: the tiny self-contained universe artifact.

Built from the contract DDL (three systems, the Weber hyper-band columns + model
row, ship classes/ships with an override, a wormhole junction), so the route
compiler, the queue resolver and repeating routes can all be exercised without
the real ``data/`` artifact.
"""

from __future__ import annotations

import pathlib
import sqlite3
from datetime import UTC, datetime

import pytest

from hvsim.flightplan import Ship
from hvsim.universe import Universe

DDL = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "universe-artifact" / "schema.sql"
DEPART = datetime(1890, 1, 1, tzinfo=UTC)
# A ship that cruises Eta (multiplier 4294) at warship 0.6c.
WARSHIP = Ship("Test Warship", 600.0, 0.6, max_hyper_band=7, hyper_cruise_velocity_c=0.6)


@pytest.fixture
def artifact_path(tmp_path) -> str:
    db = tmp_path / "u.db"
    con = sqlite3.connect(db)
    con.executescript(DDL.read_text())
    con.execute("INSERT INTO schema_meta (version) VALUES ('test')")

    def system(sid: str, z_ly: float) -> None:
        con.execute(
            "INSERT INTO star_systems (id,name,canon,is_binary,coord_x_ly,coord_y_ly,coord_z_ly) "
            "VALUES (?,?,1,0,0,0,?)",
            (sid, sid, z_ly),
        )

    def star(sid: str, sysid: str, limit_lmin: float) -> None:
        con.execute(
            "INSERT INTO stars (id,system_id,name,role,mass_solar,hyper_limit_lmin,canon) "
            "VALUES (?,?,?,'primary',1.0,?,1)",
            (sid, sysid, sid, limit_lmin),
        )

    def planet(sid: str, sysid: str, star_id: str, a_au: float) -> None:
        con.execute(
            "INSERT INTO bodies (id,system_id,parent_star_id,name,type,orbit_index,canon,"
            "orbit_determined,a_au,e,i_deg,l_deg,long_peri_deg,long_node_deg,period_days) "
            "VALUES (?,?,?,?,'planet',3,1,1,?,0,0,0,0,0,?)",
            (sid, sysid, star_id, sid, a_au, 365.25 * a_au**1.5),
        )

    system("alpha", 0.0)
    system("beta", 40.0)
    system("gamma", 71.0)
    star("alpha:s", "alpha", 20.0)
    star("beta:s", "beta", 20.0)
    star("gamma:s", "gamma", 22.0)
    planet("alpha:p1", "alpha", "alpha:s", 1.0)
    planet("alpha:far", "alpha", "alpha:s", 150.0)  # long n-space leg (forces coast)
    planet("beta:p1", "beta", "beta:s", 1.0)
    planet("gamma:p1", "gamma", "gamma:s", 1.5)

    # Hyper bands (Weber chart): Delta, Eta, Theta usable; Iota unattainable.
    for order, name, mult, bleed, unatt in [
        (4, "Delta", 2178, 72, 0),
        (7, "Eta", 4294, 56, 0),
        (8, "Theta", 5000, 52, 0),
        (9, "Iota", 6000, 48, 1),
    ]:
        con.execute(
            "INSERT INTO hyperspace_bands (band_order,name,velocity_multiplier,multiplier_canon,"
            "translation_bleed_off_pct,bleed_off_canon,unattainable,canon) "
            "VALUES (?,?,?,1,?,1,?,1)",
            (order, name, mult, bleed, unatt),
        )
    con.execute(
        "INSERT INTO hyperspace_model (id,warship_real_velocity_c,merchant_real_velocity_c,"
        "non_crash_translation_c,alpha_entry_max_velocity_c,canon) VALUES (1,0.6,0.5,0.2,0.3,1)"
    )

    # A warship class (Eta, 0.6c) + a merchant class (Delta, 0.5c).
    con.execute(
        "INSERT INTO ship_classes (id,name,navy,hull_classification,max_g,max_hyper_band,"
        "real_cruise_velocity_c,mass_tons,singleton,canon) VALUES "
        "('warbird','Warbird','TSN','BC',600,7,0.6,2500000,0,1)"
    )
    con.execute(
        "INSERT INTO ship_classes (id,name,max_g,max_hyper_band,real_cruise_velocity_c,"
        "mass_tons,singleton,canon) VALUES ('hauler','Hauler',200,4,0.5,5000000,0,1)"
    )
    # war-1 inherits the class; war-2 has a Theta upgrade override; haul-1 is a merchant.
    con.execute(
        "INSERT INTO ships (id,name,class_id,transponder,canon) "
        "VALUES ('war-1','War One','warbird','1.1.1',1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,ovr_max_hyper_band,transponder,canon) "
        "VALUES ('war-2','War Two','warbird',8,'1.1.2',1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,transponder,canon) "
        "VALUES ('haul-1','Haul One','hauler','1.2.1',1)"
    )

    con.execute(
        "INSERT INTO transit_model (id,formula,coeff_a,coeff_b,buffer_normal_s,buffer_emergency_s,"
        "canon) VALUES (1,'A*sqrt(M)+B*M^2',0.01684,6.9e-13,300,120,0)"
    )
    con.execute(
        "INSERT INTO wormhole_junctions (id,name,host_system_id,traffic_intensity,"
        "nexus_dist_lmin,nexus_bearing_deg,canon) VALUES ('bj','BJ','beta',3.0,420,30,1)"
    )
    con.execute(
        "INSERT INTO wormhole_links (id,junction_id,from_system_id,to_system_id,distance_ly,"
        "transit,canon) VALUES ('wl','bj','beta','gamma',31,'instant',1)"
    )
    con.commit()
    con.close()
    return str(db)


@pytest.fixture
def u(artifact_path: str) -> Universe:
    return Universe.open(artifact_path)
