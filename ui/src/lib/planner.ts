// Pure Flight Planner logic (Sprint 027), kept out of the component for testing.

import type { FiledRoute, PlanRequest, RepeatSpec } from './api';

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

// --- Repeating routes (Sprint 039, #59) --------------------------------------

export interface RepeatOptions {
  minLayoverH: number;
  maxLayoverH: number;
  cycles: number | null; // null = forever
}

export const DEFAULT_REPEAT: RepeatOptions = { minLayoverH: 2, maxLayoverH: 6, cycles: null };

// A repeating route is a round trip, so the planned itinerary ends back where it
// started. The engine enforces this too — it is a UI convenience, not the rule.
export function loopWaypoints(
  origin: { system: string; body: string },
  waypoints: Waypoint[],
  layover_s: number
): Waypoint[] {
  return [...waypoints, { system: origin.system, body: origin.body, layover_s }];
}

// The repeat block for a planned route: a layover range on every leg that reaches
// a body (the stops), nothing on the intermediate hyper/wormhole legs.
export function repeatSpec(filed: FiledRoute, opts: RepeatOptions): RepeatSpec {
  const min_s = Math.max(0, opts.minLayoverH) * 3600;
  const max_s = Math.max(min_s, opts.maxLayoverH * 3600);
  return {
    layovers: filed.legs.map((leg) => (leg.to_body ? { min_s, max_s } : { min_s: 0, max_s: 0 })),
    cycles: opts.cycles,
    seed: 0,
    rules: []
  };
}

// True once the loop is fileable: it must come back to the origin body.
export function isLoop(filed: FiledRoute): boolean {
  const last = filed.legs.at(-1);
  return !!last && last.to_system === filed.origin.system && last.to_body === filed.origin.body;
}

// "cycle 3" / "cycle 3 of 5" / "" — the board + detail badge for a repeating ship.
export function cycleLabel(cycle: number | null, cycles: number | null): string {
  if (cycle == null) return '';
  return cycles == null ? `cycle ${cycle}` : `cycle ${cycle} of ${cycles}`;
}
