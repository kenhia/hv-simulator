// Pure helpers for drawing a system's stars and grouping its planets by star
// (Sprint 028). A binary's stars sit at mass-ratio offsets from the barycenter
// origin; planets orbit their parent star, so colouring a planet by its parent
// makes each star's little system read as a group. Kept out of the component for
// testing, like camera.ts / planner.ts.

import type { Star, SystemBody } from './api';
import type { Vec2 } from './camera';

// Distinct star colours, primary first; cycles if a system has more stars.
export const STAR_PALETTE = ['#ffd86b', '#ff9d5c', '#9cc4ff', '#ff7a7a'];

// Neutral body colours when the parent star is unknown (Sol's synthetic bodies).
export const DEFAULT_PLANET = '#cfe0ff';
export const MOON_COLOR = '#9aa6bd';

// star id -> display colour, assigned by the order the API returns stars
// (primary first). Stable and deterministic.
export function starColors(stars: Star[]): Map<string, string> {
  const m = new Map<string, string>();
  stars.forEach((s, i) => m.set(s.id, STAR_PALETTE[i % STAR_PALETTE.length]));
  return m;
}

// A star's in-system point in AU (barycenter frame); origin if not provided.
export function starWorld(s: Star): Vec2 {
  return s.position ? { x: s.position.au.x, y: s.position.au.y } : { x: 0, y: 0 };
}

// A body's draw colour: moons stay neutral; a planet takes its parent star's
// colour so binary systems group visibly, falling back to the default planet
// colour when the parent is unknown.
export function bodyColor(body: SystemBody, starColorMap: Map<string, string>): string {
  if (body.type === 'moon') return MOON_COLOR;
  const c = body.parent_star_id ? starColorMap.get(body.parent_star_id) : undefined;
  return c ?? DEFAULT_PLANET;
}
