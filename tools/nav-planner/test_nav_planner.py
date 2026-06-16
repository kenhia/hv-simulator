"""nav-planner: graph search picks the time-optimal multi-mode route."""

from __future__ import annotations

import pathlib
import sqlite3
from datetime import UTC, datetime

import pytest
from hvsim.route import compile_route, from_filed, to_filed
from hvsim.universe import Universe

from nav_planner import plan_route

ROOT = pathlib.Path(__file__).resolve().parents[2]
DDL = ROOT / "contracts" / "universe-artifact" / "schema.sql"
DEPART = datetime(1890, 1, 1, tzinfo=UTC)


@pytest.fixture
def artifact_path(tmp_path) -> str:
    db = tmp_path / "u.db"
    con = sqlite3.connect(db)
    con.executescript(DDL.read_text())
    con.execute("INSERT INTO schema_meta (version) VALUES ('test')")

    def system(sid, z):
        con.execute(
            "INSERT INTO star_systems (id,name,canon,is_binary,coord_x_ly,coord_y_ly,coord_z_ly) "
            "VALUES (?,?,1,0,0,0,?)",
            (sid, sid, z),
        )
        con.execute(
            "INSERT INTO stars (id,system_id,name,role,mass_solar,hyper_limit_lmin,canon) "
            "VALUES (?,?,?,'primary',1.0,20.0,1)",
            (f"{sid}:s", sid, sid),
        )
        con.execute(
            "INSERT INTO bodies (id,system_id,parent_star_id,name,type,orbit_index,canon,"
            "orbit_determined,a_au,e,i_deg,l_deg,long_peri_deg,long_node_deg,period_days) "
            "VALUES (?,?,?,?,'planet',3,1,1,1.0,0,0,0,0,0,365.25)",
            (f"{sid}:p", sid, f"{sid}:s", sid),
        )

    # home --(wormhole)--> far (500 ly away; the hop beats a long hyper run).
    # mid is 5 ly from home with no wormhole.
    system("home", 0.0)
    system("mid", 5.0)
    system("far", 500.0)
    for order, name, mult in [(4, "Delta", 2178), (7, "Eta", 4294)]:
        con.execute(
            "INSERT INTO hyperspace_bands (band_order,name,velocity_multiplier,multiplier_canon,"
            "translation_bleed_off_pct,bleed_off_canon,unattainable,canon) "
            "VALUES (?,?,?,1,60,1,0,1)",
            (order, name, mult),
        )
    con.execute(
        "INSERT INTO hyperspace_model (id,warship_real_velocity_c,merchant_real_velocity_c,"
        "non_crash_translation_c,alpha_entry_max_velocity_c,canon) VALUES (1,0.6,0.5,0.2,0.3,1)"
    )
    con.execute(
        "INSERT INTO ship_classes (id,name,navy,hull_classification,max_g,max_hyper_band,"
        "real_cruise_velocity_c,singleton,canon) VALUES "
        "('warbird','Warbird','TSN','BC',600,7,0.6,0,1),('hauler','Hauler',NULL,NULL,200,4,0.5,0,1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,transponder,canon) VALUES ('war','War','warbird','1.1.1',1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,transponder,canon) VALUES ('haul','Haul','hauler','1.2.1',1)"
    )
    con.execute(
        "INSERT INTO transit_model (id,formula,coeff_a,coeff_b,buffer_normal_s,buffer_emergency_s,"
        "canon) VALUES (1,'A',0.0,0.0,300,120,0)"
    )
    con.execute(
        "INSERT INTO wormhole_junctions (id,name,host_system_id,canon) VALUES ('j','J','home',1)"
    )
    con.execute(
        "INSERT INTO wormhole_links (id,junction_id,from_system_id,to_system_id,distance_ly,"
        "transit,canon) VALUES ('wl','j','home','far',500,'instant',1)"
    )
    # A non-wormhole annotation in the same table must NOT be used as a hop.
    con.execute(
        "INSERT INTO wormhole_links (id,from_system_id,to_system_id,transit,canon) "
        "VALUES ('hl','home','mid',NULL,1)"
    )
    con.commit()
    con.close()
    return str(db)


@pytest.fixture
def u(artifact_path: str) -> Universe:
    return Universe.open(artifact_path)


def test_picks_wormhole_when_faster(u: Universe) -> None:
    route = plan_route(u, "war", "home", "home:p", "far", "far:p", DEPART)
    assert any(leg.mode == "wormhole" for leg in route.legs)
    # The final body is reached (trailing n-space hop after the wormhole).
    assert route.legs[-1].to_body == "far:p"


def test_pure_hyper_when_no_wormhole(u: Universe) -> None:
    route = plan_route(u, "war", "home", "home:p", "mid", "mid:p", DEPART)
    assert [leg.mode for leg in route.legs] == ["hyper"]
    assert route.legs[-1].to_body == "mid:p"  # the hyper approach targets the body


def test_non_instant_link_is_not_a_wormhole_hop(u: Universe) -> None:
    # home->mid has only a hyper_leg annotation (transit NULL), not a wormhole.
    route = plan_route(u, "war", "home", "home:p", "mid", "mid:p", DEPART)
    assert all(leg.mode != "wormhole" for leg in route.legs)


def test_faster_ship_plans_faster(u: Universe) -> None:
    fast = compile_route(plan_route(u, "war", "home", "home:p", "mid", "mid:p", DEPART), u)
    slow = compile_route(plan_route(u, "haul", "home", "home:p", "mid", "mid:p", DEPART), u)
    assert fast.arrival < slow.arrival


def test_plan_round_trips_and_flies(u: Universe) -> None:
    route = plan_route(u, "war", "home", "home:p", "far", "far:p", DEPART)
    doc = to_filed(route, "1.1.1")  # war's transponder
    reloaded = from_filed(doc, u)
    assert compile_route(reloaded, u).arrival == compile_route(route, u).arrival


def test_unreachable_raises(u: Universe) -> None:
    with pytest.raises(ValueError):
        plan_route(u, "war", "home", "home:p", "nowhere", "nowhere:p", DEPART)
