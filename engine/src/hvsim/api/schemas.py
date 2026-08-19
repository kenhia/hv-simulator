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
    rate: float | None = Field(default=None, ge=0)  # 0 = frozen (dev pause)
    jump_to: datetime | None = None
    advance_seconds: float | None = None


class FiledLegIn(BaseModel):
    mode: str  # nspace | hyper | wormhole
    to_system: str
    to_body: str | None = None
    layover_s: float = Field(default=0.0, ge=0)


class FiledOriginIn(BaseModel):
    system: str
    body: str


class ShipCatalogEntry(BaseModel):
    transponder: str
    name: str
    nation_code: str  # first transponder component
    ship_class: str | None
    military: bool  # has a navy -> drives the UI min-layover rule
    under_way: bool  # in motion now (can't re-file without 409); arrived ≠ under way
    location_system: str | None  # current navigable point (for origin prefill), if at rest
    location_body: str | None


class PlanWaypoint(BaseModel):
    system: str
    body: str
    layover_s: float = Field(default=0.0, ge=0)


class PlanRequest(BaseModel):
    """Plan a multi-destination route to preview (not file). Ship by transponder."""

    ship: str
    origin: FiledOriginIn
    waypoints: list[PlanWaypoint]
    depart_at: datetime | None = None


class LayoverRangeIn(BaseModel):
    """One stop's layover range on a repeating route (equal bounds == fixed)."""

    min_s: float = Field(ge=0)
    max_s: float = Field(ge=0)


class CycleRuleIn(BaseModel):
    """Override a stop's layover on every N-th cycle ("every 5th trip, 12 h")."""

    every: int = Field(ge=1)
    stop: int = Field(ge=0)
    layover_s: float = Field(ge=0)


class RepeatIn(BaseModel):
    """Turn a filed route into a loop the ship lives on (Sprint 039, #59).

    ``layovers`` is index-aligned with the legs and supersedes their ``layover_s``;
    ``cycles`` is null for forever. The last leg must return to the origin.
    """

    layovers: list[LayoverRangeIn] = Field(default_factory=list)
    cycles: int | None = Field(default=None, ge=1)
    seed: int = 0
    rules: list[CycleRuleIn] = Field(default_factory=list)


class FiledRouteIn(BaseModel):
    """A planner-produced filed route (the nav-planner JSON body). Ship by transponder.

    With ``repeat`` set, the legs describe **one cycle** of a repeating itinerary
    rather than a one-shot trip, and the route is filed as a repeating route.
    """

    model_config = {"extra": "ignore"}  # ignore the doc's "schema" marker
    ship: str  # transponder (nation.class.hull)
    origin: FiledOriginIn
    legs: list[FiledLegIn] = Field(min_length=1)
    depart_at: datetime | None = None
    repeat: RepeatIn | None = None


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


class BandOut(BaseModel):
    """The active hyperspace band (set only during a hyper_cruise leg)."""

    order: int
    name: str | None
    velocity_multiplier: float  # apparent = velocity_multiplier x real velocity


class AccelOut(BaseModel):
    """Current felt acceleration (real). Null at rest / while coasting."""

    m_s2: float
    km_s2: float
    g: float


class StateOut(BaseModel):
    when: datetime
    # idle | predeparture | transit | layover | hyper_cruise | queued | wormhole_transit | arrived
    phase: str
    segment_seq: int | None
    position: PositionOut
    velocity: VelocityOut
    eta: datetime | None  # overall arrival
    percent_complete: float | None
    destination: str | None
    distance_to_destination_km: float | None
    distance_from_origin_km: float | None = None  # from the origin body (co-frame only)
    acceleration: AccelOut | None = None  # current felt accel (null at rest/coast)
    subjective_time_delta_s: float | None = None  # reserved (relativity deferred)
    # Cross-system context (Sprint 018). system is None on an interstellar leg.
    system: str | None = None
    frame: str = "heliocentric"  # heliocentric | galactic
    transponder: str | None = None
    queue_position: int | None = None  # set while phase == "queued" (1 == next to transit)
    # Repeating routes (#59): the cycle being flown (1-based) out of `cycles` (null
    # == forever). Both null for a one-shot route.
    cycle: int | None = None
    cycles: int | None = None
    # Set only in hyper: velocity (above) is the *apparent* speed; real = apparent /
    # band.velocity_multiplier. Lets the UI show "0.382c real · 1640c apparent (Zeta)".
    band: BandOut | None = None


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


class RouteOut(BaseModel):
    transponder: str
    status: str
    origin: FiledOriginIn
    depart_at: datetime
    arrival: datetime
    total_duration_seconds: float
    total_duration_human: str
    segments: list[SegmentOut]
    # For a repeating route these are the *active cycle's* segments (#59).
    cycle: int | None = None
    cycles: int | None = None


class PlanOut(BaseModel):
    """A planned (not filed) route: the filed-route doc to POST + a compiled preview."""

    filed: dict  # the filed-route JSON; POST to /fleet/routes to commit
    route: RouteOut  # compiled preview (segments + ETA)


class FleetEntry(BaseModel):
    transponder: str
    ship: str
    phase: str
    system: str | None
    eta: datetime | None
    percent_complete: float | None
    queue_position: int | None = None  # set while phase == "queued" (1 == next to transit)
    filed_at: datetime | None = None  # when the route was filed (for board sort)
    cycle: int | None = None  # repeating routes: the cycle in flight (1-based)
    cycles: int | None = None  # ... out of this many (null == forever)


class FleetOut(BaseModel):
    when: datetime
    ships: list[FleetEntry]


class JunctionQueueEntry(BaseModel):
    transponder: str | None  # None = phantom (background) traffic
    position: int  # 1 == next to transit
    mass_tons: float
    transit_eta: datetime


class JunctionQueue(BaseModel):
    junction_id: str
    when: datetime
    traffic_intensity: float | None = None  # the junction's mean-queue-depth knob
    entries: list[JunctionQueueEntry]


class StarOut(BaseModel):
    id: str
    name: str | None
    role: str | None
    spectral_type: str | None
    mass_solar: float | None
    hyper_limit_lmin: float | None
    # In-system position (km+AU), barycenter-centred. A binary's stars sit at their
    # mass-ratio offsets; a single star sits at the origin. None if not computable.
    position: PositionOut | None = None


class SystemDetail(BaseModel):
    id: str
    name: str
    star_nation_id: str | None
    is_binary: bool
    distance_ly: float | None
    coordinates: dict | None  # {x_ly,y_ly,z_ly} or null (unplaced)
    primary_hyper_limit_lmin: float | None
    primary_hyper_limit_au: float | None  # the ring radius the system view draws
    stars: list[StarOut]
    binary: dict | None  # separation/period (binaries row) or null


class PlaceOut(BaseModel):
    id: str
    name: str | None
    type: str | None
    rides_on_body_id: str | None
    # Position (km+AU) when the place rides a body; null for free-floating / nexus.
    position: PositionOut | None = None


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
