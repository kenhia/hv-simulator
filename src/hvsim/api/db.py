"""SQLAlchemy models and engine setup (SQLite).

Tables: ships, flight_plans, waypoints, and the compiled segments. A segment row
holds either a transit's trajectory floats (origin/direction/profile) or, for a
layover, the body the ship is docked at. Storing the compiled segments is what
lets a state query be a pure lookup + one kinematics eval — see
``serialize.py`` for the row <-> domain mapping.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


def _new_id() -> str:
    return uuid.uuid4().hex


class ShipRow(Base):
    __tablename__ = "ships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String)
    max_accel_g: Mapped[float] = mapped_column(Float)
    max_velocity_c: Mapped[float] = mapped_column(Float)
    home_body: Mapped[str] = mapped_column(String, default="earth")
    status: Mapped[str] = mapped_column(String, default="idle")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class FlightPlanRow(Base):
    __tablename__ = "flight_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_id)
    ship_id: Mapped[str] = mapped_column(ForeignKey("ships.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="active")  # active|complete|aborted
    origin: Mapped[str] = mapped_column(String)
    depart_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class WaypointRow(Base):
    __tablename__ = "waypoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flight_plan_id: Mapped[str] = mapped_column(ForeignKey("flight_plans.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(String)
    layover_s: Mapped[float] = mapped_column(Float, default=0.0)


class SegmentRow(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flight_plan_id: Mapped[str] = mapped_column(ForeignKey("flight_plans.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String)  # transit|layover
    t_start: Mapped[datetime] = mapped_column(DateTime)
    t_end: Mapped[datetime] = mapped_column(DateTime)

    body: Mapped[str | None] = mapped_column(String, nullable=True)  # layover

    # Transit trajectory (SI). Nullable because layover rows omit them.
    origin_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_z: Mapped[float | None] = mapped_column(Float, nullable=True)
    dir_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    dir_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    dir_z: Mapped[float | None] = mapped_column(Float, nullable=True)
    prof_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    prof_accel: Mapped[float | None] = mapped_column(Float, nullable=True)
    prof_v_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    prof_v_peak: Mapped[float | None] = mapped_column(Float, nullable=True)
    prof_t_accel: Mapped[float | None] = mapped_column(Float, nullable=True)
    prof_t_coast: Mapped[float | None] = mapped_column(Float, nullable=True)


def make_engine(database_url: str) -> Engine:
    """Create an engine; for SQLite, allow cross-thread use (uvicorn workers)."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
