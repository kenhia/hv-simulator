"""Map compiled-plan domain objects to/from DB rows.

The domain ``Segment``/``Trajectory``/``Profile`` are pure dataclasses; here we
flatten them into ``SegmentRow`` columns and rebuild them on read, so
``state_at`` runs against stored data with no recompilation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from hvsim.flightplan import CompiledPlan, FlightPlan, Segment, Ship, Waypoint
from hvsim.kinematics import Profile, Trajectory, Vec3

from .db import FlightPlanRow, SegmentRow, ShipRow, WaypointRow


def as_utc(dt: datetime) -> datetime:
    """Attach UTC to a naive datetime (SQLite drops tzinfo on store)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def segment_to_row(seg: Segment, plan_id: str) -> SegmentRow:
    row = SegmentRow(
        flight_plan_id=plan_id,
        seq=seg.seq,
        kind=seg.kind,
        t_start=seg.t_start,
        t_end=seg.t_end,
    )
    if seg.kind == "transit":
        assert seg.trajectory is not None
        tr = seg.trajectory
        p = tr.profile
        row.origin_x, row.origin_y, row.origin_z = tr.origin
        row.dir_x, row.dir_y, row.dir_z = tr.direction
        row.prof_distance = p.distance
        row.prof_accel = p.accel
        row.prof_v_max = p.v_max
        row.prof_v_peak = p.v_peak
        row.prof_t_accel = p.t_accel
        row.prof_t_coast = p.t_coast
    else:
        row.body = seg.body
    return row


def row_to_segment(row: SegmentRow) -> Segment:
    t_start, t_end = as_utc(row.t_start), as_utc(row.t_end)
    if row.kind == "transit":
        trajectory = Trajectory(
            origin=Vec3(row.origin_x, row.origin_y, row.origin_z),
            direction=Vec3(row.dir_x, row.dir_y, row.dir_z),
            profile=Profile(
                distance=row.prof_distance,
                accel=row.prof_accel,
                v_max=row.prof_v_max,
                v_peak=row.prof_v_peak,
                t_accel=row.prof_t_accel,
                t_coast=row.prof_t_coast,
            ),
        )
        return Segment(row.seq, "transit", t_start, t_end, trajectory=trajectory)
    return Segment(row.seq, "layover", t_start, t_end, body=row.body)


def load_compiled(session: Session, plan_row: FlightPlanRow, ship_row: ShipRow) -> CompiledPlan:
    """Rebuild a CompiledPlan from its stored rows."""
    wp_rows = session.scalars(
        select(WaypointRow)
        .where(WaypointRow.flight_plan_id == plan_row.id)
        .order_by(WaypointRow.seq)
    ).all()
    waypoints = [Waypoint(w.body, timedelta(seconds=w.layover_s)) for w in wp_rows]

    ship = Ship(ship_row.name, ship_row.max_accel_g, ship_row.max_velocity_c)
    plan = FlightPlan(ship, plan_row.origin, waypoints, as_utc(plan_row.depart_at))

    seg_rows = session.scalars(
        select(SegmentRow).where(SegmentRow.flight_plan_id == plan_row.id).order_by(SegmentRow.seq)
    ).all()
    return CompiledPlan(plan, [row_to_segment(r) for r in seg_rows])
