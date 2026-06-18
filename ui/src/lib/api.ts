// Typed client for the engine's read API. Paths are absolute (same-origin in
// production under /ui; the Vite dev server proxies them to the engine).

export interface SystemCoords {
  x_ly: number;
  y_ly: number;
  z_ly: number;
}

export interface System {
  id: string;
  name: string;
  star_nation_id: string | null;
  is_binary: boolean;
  distance_ly: number | null;
  coordinates: SystemCoords | null; // null => not placed (stubbed system)
}

export interface WormholeLink {
  id: string;
  junction_id: string | null;
  from_system_id: string;
  to_system_id: string | null;
  transit: string | null; // "instant" for true wormholes
}

export interface Junction {
  id: string;
  name: string;
  host_system_id: string | null;
  traffic_intensity: number | null;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export const fetchSystems = () => getJSON<System[]>('/systems');
export const fetchWormholes = () => getJSON<WormholeLink[]>('/wormholes');
export const fetchJunctions = () => getJSON<Junction[]>('/junctions');

// --- System detail (Sprint 022: the system-zoom view) ------------------------

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface Position {
  km: Vec3;
  au: Vec3;
  distance_from_sun_km: number;
  distance_from_sun_au: number;
}

export interface Star {
  id: string;
  name: string | null;
  role: string | null;
  spectral_type: string | null;
  mass_solar: number | null;
  hyper_limit_lmin: number | null;
}

export interface SystemDetail {
  id: string;
  name: string;
  star_nation_id: string | null;
  is_binary: boolean;
  distance_ly: number | null;
  coordinates: SystemCoords | null;
  primary_hyper_limit_lmin: number | null;
  primary_hyper_limit_au: number | null; // the hyper-limit ring radius
  stars: Star[];
  binary: Record<string, unknown> | null;
}

export interface SystemBody {
  id: string;
  name: string;
  type: string | null;
  position: Position;
}

export interface Place {
  id: string;
  name: string | null;
  type: string | null;
  rides_on_body_id: string | null;
  position: Position | null; // present when the place rides a body
}

export const fetchSystemDetail = (id: string) => getJSON<SystemDetail>(`/systems/${id}`);
export const fetchSystemBodies = (id: string, at?: string) =>
  getJSON<SystemBody[]>(`/systems/${id}/bodies${at ? `?at=${encodeURIComponent(at)}` : ''}`);
export const fetchSystemPlaces = (id: string, at?: string) =>
  getJSON<Place[]>(`/systems/${id}/places${at ? `?at=${encodeURIComponent(at)}` : ''}`);

// --- Live fleet (Sprint 023) -------------------------------------------------

export interface ClockOut {
  now: string;
  rate: number;
  sim_epoch: string;
  real_epoch: string;
  dev_controls_enabled: boolean;
}

export interface Velocity {
  km_s: Vec3;
  speed_km_s: number;
  fraction_c: number;
}

export interface ShipState {
  when: string;
  phase: string;
  segment_seq: number | null;
  position: Position;
  velocity: Velocity;
  eta: string | null;
  percent_complete: number | null;
  destination: string | null;
  system: string | null;
  frame: 'heliocentric' | 'galactic';
  transponder: string | null;
  queue_position: number | null;
}

export interface FleetEntry {
  transponder: string;
  ship: string;
  phase: string;
  system: string | null;
  eta: string | null;
  percent_complete: number | null;
  queue_position: number | null;
}

export interface RouteSegment {
  seq: number;
  kind: string;
  t_start: string;
  t_end: string;
  duration_seconds: number;
  duration_human: string;
  body: string | null;
}

export interface RouteOut {
  transponder: string;
  status: string;
  origin: Record<string, string>;
  depart_at: string;
  arrival: string;
  total_duration_seconds: number;
  total_duration_human: string;
  segments: RouteSegment[];
}

export const fetchClock = () => getJSON<ClockOut>('/clock');

export interface ClockUpdate {
  rate?: number;
  jump_to?: string;
  advance_seconds?: number;
}

export async function putClock(body: ClockUpdate): Promise<ClockOut> {
  const res = await fetch('/clock', {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`PUT /clock -> ${res.status}`);
  return (await res.json()) as ClockOut;
}
export const fetchFleet = () => getJSON<{ when: string; ships: FleetEntry[] }>('/fleet');
export const fetchShipState = (tp: string) => getJSON<ShipState>(`/fleet/${tp}/state`);
export const fetchShipRoute = (tp: string) => getJSON<RouteOut>(`/fleet/${tp}/route`);

// --- Junction transit queue (Sprint 024; engine endpoint from 020) -----------

export interface JunctionQueueEntry {
  transponder: string | null; // null = phantom (background) traffic
  position: number; // 1 = next to transit
  mass_tons: number;
  transit_eta: string;
}

export interface JunctionQueue {
  junction_id: string;
  when: string;
  traffic_intensity: number | null;
  entries: JunctionQueueEntry[];
}

export const fetchJunctionQueue = (id: string, at?: string) =>
  getJSON<JunctionQueue>(`/junctions/${id}/queue${at ? `?at=${encodeURIComponent(at)}` : ''}`);

// --- Controller: ship catalog + plan/file (Sprint 027) -----------------------

export interface ShipCatalogEntry {
  transponder: string;
  name: string;
  nation_code: string;
  ship_class: string | null;
  military: boolean;
  has_active_route: boolean;
}

export interface FiledLeg {
  mode: string;
  to_system: string;
  to_body: string | null;
  layover_s: number;
}

export interface FiledRoute {
  schema: string;
  ship: string;
  origin: { system: string; body: string };
  depart_at: string;
  legs: FiledLeg[];
}

export interface PlanRequest {
  ship: string;
  origin: { system: string; body: string };
  waypoints: { system: string; body: string; layover_s: number }[];
}

export interface PlanResult {
  filed: FiledRoute;
  route: RouteOut;
}

async function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export const fetchShipCatalog = () => getJSON<ShipCatalogEntry[]>('/fleet/ships');
export const postPlan = (req: PlanRequest) => send<PlanResult>('POST', '/plan', req);
export const postFleetRoute = (filed: FiledRoute) => send<RouteOut>('POST', '/fleet/routes', filed);
export const deleteRoute = (tp: string) => send<unknown>('DELETE', `/fleet/${tp}/route`);

export interface Galaxy {
  systems: System[];
  links: WormholeLink[];
  junctions: Junction[];
}

export async function fetchGalaxy(): Promise<Galaxy> {
  const [systems, links, junctions] = await Promise.all([
    fetchSystems(),
    fetchWormholes(),
    fetchJunctions()
  ]);
  return { systems, links, junctions };
}
