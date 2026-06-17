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
