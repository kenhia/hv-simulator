// Split a route's segments into legs for the multi-leg Ship Timeline (Sprint 036,
// #73). A leg = the travel segments up to and including the layover that ends them
// (the dwell at a waypoint); the final leg has no trailing layover (it arrives).
// Pure + testable; the component renders one strip per leg.

import type { RouteSegment } from './api';

export function splitLegs(segments: RouteSegment[]): RouteSegment[][] {
  const legs: RouteSegment[][] = [];
  let cur: RouteSegment[] = [];
  for (const s of segments) {
    cur.push(s);
    if (s.kind === 'layover') {
      legs.push(cur);
      cur = [];
    }
  }
  if (cur.length) legs.push(cur);
  return legs;
}

export function legDurationS(leg: RouteSegment[]): number {
  return leg.reduce((a, s) => a + (s.duration_seconds || 0), 0);
}

// The body a leg ends at: its layover body, else the last segment's body.
export function legLabel(leg: RouteSegment[]): string {
  const layover = leg.find((s) => s.kind === 'layover');
  return layover?.body ?? leg.at(-1)?.body ?? '—';
}

// Which leg the ship is on (0-based) + local progress [0,1] within it, from the
// overall route percent — so the progress marker lands on the active strip.
export function legProgress(
  legs: RouteSegment[][],
  percent: number
): { index: number; local: number } {
  const total = legs.reduce((a, l) => a + legDurationS(l), 0) || 1;
  let elapsed = Math.min(Math.max(percent, 0), 1) * total;
  for (let i = 0; i < legs.length; i++) {
    const d = legDurationS(legs[i]) || 1;
    if (elapsed <= d || i === legs.length - 1) return { index: i, local: Math.min(elapsed / d, 1) };
    elapsed -= d;
  }
  return { index: 0, local: 0 };
}
