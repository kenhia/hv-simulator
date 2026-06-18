// Pure Flight Planner logic (Sprint 027), kept out of the component for testing.

import type { FiledRoute, PlanRequest } from './api';

export const CIVILIAN_LAYOVER_S = 2 * 3600; // UI-enforced min layover (007); editable
export const MILITARY_LAYOVER_S = 0;

export interface Waypoint {
  system: string;
  body: string;
  layover_s: number;
}

// Default per-waypoint layover by ship type (non-military clears arrival+departure).
export function defaultLayoverS(military: boolean): number {
  return military ? MILITARY_LAYOVER_S : CIVILIAN_LAYOVER_S;
}

// Ready to plan once a ship, an origin (system+body), and ≥1 complete waypoint exist.
export function canPlan(
  ship: string,
  origin: { system: string; body: string },
  waypoints: Waypoint[]
): boolean {
  if (!ship || !origin.system || !origin.body) return false;
  return waypoints.length > 0 && waypoints.every((w) => w.system && w.body);
}

export function toPlanRequest(
  ship: string,
  origin: { system: string; body: string },
  waypoints: Waypoint[]
): PlanRequest {
  return { ship, origin, waypoints };
}

// The ordered system path a route visits — origin then each leg's destination
// system, de-duplicated consecutively — for highlighting on the galaxy map.
export function routeSystems(filed: FiledRoute): string[] {
  const out = [filed.origin.system];
  for (const leg of filed.legs) {
    if (out[out.length - 1] !== leg.to_system) out.push(leg.to_system);
  }
  return out;
}
