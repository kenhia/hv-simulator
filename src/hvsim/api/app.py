"""FastAPI application factory wiring the domain logic to HTTP + SQLite.

``create_app()`` builds an app with its own engine, session factory, and
``SimClock`` singleton, so tests can inject a temp database and a fixed clock.
For production/Docker, run with uvicorn's factory mode:
``uvicorn --factory hvsim.api.app:create_app``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from hvsim.clock import SimClock
from hvsim.ephemeris import BODIES, heliocentric_position, list_bodies
from hvsim.flightplan import FlightPlan, Ship, Waypoint, compile_plan, state_at
from hvsim.kinematics import ZERO, Vec3

from .db import (
    FlightPlanRow,
    SegmentRow,
    ShipRow,
    WaypointRow,
    init_db,
    make_engine,
    make_session_factory,
)
from .schemas import (
    BodyOut,
    ClockOut,
    ClockUpdate,
    FlightPlanCreate,
    FlightPlanOut,
    SegmentOut,
    ShipCreate,
    ShipDetail,
    ShipOut,
    StateOut,
)
from .serialize import as_utc, load_compiled, segment_to_row
from .units import human_duration, position_out, velocity_out

DEFAULT_DB_URL = "sqlite:///hvsim.db"


def create_app(
    database_url: str | None = None,
    clock: SimClock | None = None,
    dev_clock: bool | None = None,
) -> FastAPI:
    database_url = database_url or os.environ.get("HVSIM_DB", DEFAULT_DB_URL)
    if dev_clock is None:
        dev_clock = bool(os.environ.get("HVSIM_DEV_CLOCK"))

    engine = make_engine(database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)

    app = FastAPI(title="Honorverse Ship Simulator", version="0.1.0")
    app.state.clock = clock or SimClock()
    app.state.dev_clock = dev_clock

    def get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    def get_clock() -> SimClock:
        return app.state.clock

    def resolve_when(at: datetime | None) -> datetime:
        return as_utc(at) if at is not None else app.state.clock.now()

    def require_body(name: str) -> str:
        key = name.lower()
        if key not in BODIES:
            raise HTTPException(422, f"unknown body {name!r}")
        return key

    def get_ship(ship_id: str, session: Session) -> ShipRow:
        ship = session.get(ShipRow, ship_id)
        if ship is None:
            raise HTTPException(404, f"ship {ship_id!r} not found")
        return ship

    def active_plan(session: Session, ship_id: str) -> FlightPlanRow | None:
        return session.scalars(
            select(FlightPlanRow).where(
                FlightPlanRow.ship_id == ship_id, FlightPlanRow.status == "active"
            )
        ).first()

    def ship_state(session: Session, ship: ShipRow, when: datetime) -> StateOut:
        plan_row = active_plan(session, ship.id)
        if plan_row is None:
            pos = Vec3(*heliocentric_position(ship.home_body, when))
            return StateOut(
                when=when,
                phase="idle",
                segment_seq=None,
                position=position_out(pos),
                velocity=velocity_out(ZERO),
                eta=None,
                percent_complete=None,
                destination=None,
                distance_to_destination_km=None,
            )

        compiled = load_compiled(session, plan_row, ship)
        st = state_at(compiled, when)
        depart, arrival = compiled.depart_at, compiled.arrival
        span = (arrival - depart).total_seconds()
        pct = min(max((when - depart).total_seconds() / span, 0.0), 1.0) if span > 0 else None
        destination = compiled.plan.waypoints[-1].body
        dest_pos = Vec3(*heliocentric_position(destination, when))
        return StateOut(
            when=when,
            phase=st.phase,
            segment_seq=st.segment_seq,
            position=position_out(st.position),
            velocity=velocity_out(st.velocity),
            eta=arrival,
            percent_complete=pct,
            destination=destination,
            distance_to_destination_km=(dest_pos - st.position).norm() / 1e3,
        )

    def flightplan_out(session: Session, plan_row: FlightPlanRow) -> FlightPlanOut:
        rows = session.scalars(
            select(SegmentRow)
            .where(SegmentRow.flight_plan_id == plan_row.id)
            .order_by(SegmentRow.seq)
        ).all()
        segments = [
            SegmentOut(
                seq=r.seq,
                kind=r.kind,
                t_start=as_utc(r.t_start),
                t_end=as_utc(r.t_end),
                duration_seconds=(r.t_end - r.t_start).total_seconds(),
                duration_human=human_duration((r.t_end - r.t_start).total_seconds()),
                body=r.body,
            )
            for r in rows
        ]
        depart = as_utc(plan_row.depart_at)
        arrival = segments[-1].t_end if segments else depart
        total = (arrival - depart).total_seconds()
        return FlightPlanOut(
            id=plan_row.id,
            ship_id=plan_row.ship_id,
            status=plan_row.status,
            origin=plan_row.origin,
            depart_at=depart,
            arrival=arrival,
            total_duration_seconds=total,
            total_duration_human=human_duration(total),
            segments=segments,
        )

    def clock_out() -> ClockOut:
        c = app.state.clock
        return ClockOut(
            now=c.now(),
            rate=c.rate,
            sim_epoch=as_utc(c.sim_epoch),
            real_epoch=as_utc(c.real_epoch),
            dev_controls_enabled=app.state.dev_clock,
        )

    # --- routes -----------------------------------------------------------------

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ships", response_model=ShipOut, status_code=201)
    def create_ship(body: ShipCreate, session: Session = Depends(get_db)) -> ShipRow:
        require_body(body.home_body)
        ship = ShipRow(
            name=body.name,
            max_accel_g=body.max_accel_g,
            max_velocity_c=body.max_velocity_c,
            home_body=body.home_body.lower(),
            status="idle",
            created_at=datetime.now(UTC),
        )
        session.add(ship)
        session.commit()
        return ship

    @app.get("/ships", response_model=list[ShipDetail])
    def list_ships(session: Session = Depends(get_db)) -> list[ShipDetail]:
        when = app.state.clock.now()
        ships = session.scalars(select(ShipRow)).all()
        return [
            ShipDetail(
                **ShipOut.model_validate(s, from_attributes=True).model_dump(),
                state=ship_state(session, s, when),
            )
            for s in ships
        ]

    @app.get("/ships/{ship_id}", response_model=ShipDetail)
    def get_ship_detail(
        ship_id: str, at: datetime | None = None, session: Session = Depends(get_db)
    ) -> ShipDetail:
        ship = get_ship(ship_id, session)
        return ShipDetail(
            **ShipOut.model_validate(ship, from_attributes=True).model_dump(),
            state=ship_state(session, ship, resolve_when(at)),
        )

    @app.get("/ships/{ship_id}/state", response_model=StateOut)
    def get_ship_state(
        ship_id: str, at: datetime | None = None, session: Session = Depends(get_db)
    ) -> StateOut:
        ship = get_ship(ship_id, session)
        return ship_state(session, ship, resolve_when(at))

    @app.post("/ships/{ship_id}/flightplan", response_model=FlightPlanOut, status_code=201)
    def file_flightplan(
        ship_id: str, body: FlightPlanCreate, session: Session = Depends(get_db)
    ) -> FlightPlanOut:
        ship = get_ship(ship_id, session)
        if active_plan(session, ship_id) is not None:
            raise HTTPException(409, "ship already has an active flight plan")

        origin = require_body(body.origin) if body.origin else ship.home_body
        for wp in body.waypoints:
            require_body(wp.body)
        depart_at = as_utc(body.depart_at) if body.depart_at else app.state.clock.now()

        domain_ship = Ship(ship.name, ship.max_accel_g, ship.max_velocity_c)
        plan = FlightPlan(
            domain_ship,
            origin,
            [
                Waypoint(wp.body.lower(), timedelta(seconds=wp.layover_seconds))
                for wp in body.waypoints
            ],
            depart_at,
        )
        compiled = compile_plan(plan)

        plan_row = FlightPlanRow(
            ship_id=ship.id,
            status="active",
            origin=origin,
            depart_at=depart_at,
            created_at=datetime.now(UTC),
        )
        session.add(plan_row)
        session.flush()  # assign plan_row.id
        for i, wp in enumerate(body.waypoints):
            session.add(
                WaypointRow(
                    flight_plan_id=plan_row.id,
                    seq=i,
                    body=wp.body.lower(),
                    layover_s=wp.layover_seconds,
                )
            )
        for seg in compiled.segments:
            session.add(segment_to_row(seg, plan_row.id))
        ship.status = "active"
        session.commit()
        return flightplan_out(session, plan_row)

    @app.get("/ships/{ship_id}/flightplan", response_model=FlightPlanOut)
    def get_flightplan(ship_id: str, session: Session = Depends(get_db)) -> FlightPlanOut:
        get_ship(ship_id, session)
        plan_row = active_plan(session, ship_id)
        if plan_row is None:
            raise HTTPException(404, "no active flight plan")
        return flightplan_out(session, plan_row)

    @app.delete("/ships/{ship_id}/flightplan")
    def abort_flightplan(ship_id: str, session: Session = Depends(get_db)) -> dict[str, str]:
        ship = get_ship(ship_id, session)
        plan_row = active_plan(session, ship_id)
        if plan_row is None:
            raise HTTPException(404, "no active flight plan")
        plan_row.status = "aborted"
        ship.status = "idle"
        session.commit()
        return {"id": plan_row.id, "status": "aborted"}

    @app.get("/bodies", response_model=list[BodyOut])
    def get_bodies(at: datetime | None = None) -> list[BodyOut]:
        when = resolve_when(at)
        return [
            BodyOut(
                name=info["name"],
                kind=info["kind"],
                parent=info["parent"],
                position=position_out(Vec3(*heliocentric_position(info["name"], when))),
            )
            for info in list_bodies()
        ]

    @app.get("/bodies/{body_id}/state", response_model=BodyOut)
    def get_body_state(body_id: str, at: datetime | None = None) -> BodyOut:
        name = body_id.lower()
        if name not in BODIES:
            raise HTTPException(404, f"unknown body {body_id!r}")
        when = resolve_when(at)
        info = next(b for b in list_bodies() if b["name"] == name)
        return BodyOut(
            name=name,
            kind=info["kind"],
            parent=info["parent"],
            position=position_out(Vec3(*heliocentric_position(name, when))),
        )

    @app.get("/clock", response_model=ClockOut)
    def get_clock_state() -> ClockOut:
        return clock_out()

    @app.put("/clock", response_model=ClockOut)
    def update_clock(body: ClockUpdate) -> ClockOut:
        if not app.state.dev_clock:
            raise HTTPException(403, "clock controls are disabled (set HVSIM_DEV_CLOCK)")
        c = app.state.clock
        if body.rate is not None:
            c.set_rate(body.rate)
        if body.jump_to is not None:
            c.jump_to(as_utc(body.jump_to))
        if body.advance_seconds is not None:
            c.advance(timedelta(seconds=body.advance_seconds))
        return clock_out()

    return app
