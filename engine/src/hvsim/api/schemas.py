"""Pydantic v2 request/response models — the API's human-unit contract.

Internally everything is SI (metres, m/s); these schemas carry km + AU for
positions, km/s + fraction of c for velocity, g for acceleration, and durations
as seconds + a human string. Raw SI never appears in a response.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Vector3(BaseModel):
    x: float
    y: float
    z: float


# --- requests -------------------------------------------------------------------


class ShipCreate(BaseModel):
    name: str
    max_accel_g: float = Field(gt=0)
    max_velocity_c: float = Field(gt=0, le=1.0)
    home_body: str = "earth"


class WaypointIn(BaseModel):
    body: str
    layover_seconds: float = Field(default=0.0, ge=0)


class FlightPlanCreate(BaseModel):
    waypoints: list[WaypointIn] = Field(min_length=1)
    origin: str | None = None  # defaults to the ship's home_body
    depart_at: datetime | None = None  # defaults to clock.now()


class ClockUpdate(BaseModel):
    rate: float | None = Field(default=None, gt=0)
    jump_to: datetime | None = None
    advance_seconds: float | None = None


# --- responses ------------------------------------------------------------------


class PositionOut(BaseModel):
    km: Vector3
    au: Vector3
    distance_from_sun_km: float
    distance_from_sun_au: float


class VelocityOut(BaseModel):
    km_s: Vector3
    speed_km_s: float
    fraction_c: float


class StateOut(BaseModel):
    when: datetime
    phase: str  # idle | predeparture | transit | layover | arrived
    segment_seq: int | None
    position: PositionOut
    velocity: VelocityOut
    eta: datetime | None  # overall arrival
    percent_complete: float | None
    destination: str | None
    distance_to_destination_km: float | None
    subjective_time_delta_s: float | None = None  # reserved (relativity deferred)


class ShipOut(BaseModel):
    id: str
    name: str
    max_accel_g: float
    max_velocity_c: float
    home_body: str
    status: str


class ShipDetail(ShipOut):
    state: StateOut


class SegmentOut(BaseModel):
    seq: int
    kind: str
    t_start: datetime
    t_end: datetime
    duration_seconds: float
    duration_human: str
    body: str | None = None


class FlightPlanOut(BaseModel):
    id: str
    ship_id: str
    status: str
    origin: str
    depart_at: datetime
    arrival: datetime
    total_duration_seconds: float
    total_duration_human: str
    segments: list[SegmentOut]


class BodyOut(BaseModel):
    name: str
    kind: str
    parent: str | None
    position: PositionOut


class ClockOut(BaseModel):
    now: datetime
    rate: float
    sim_epoch: datetime
    real_epoch: datetime
    dev_controls_enabled: bool
