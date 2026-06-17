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
