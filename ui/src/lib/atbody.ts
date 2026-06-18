// Group at-rest ships by the body they're parked at (Sprint 032), so the system
// map can list them on a leader off the planet label instead of overlapping dots.
// Pure + testable; the component supplies AU positions.

export interface Located {
  id: string;
  x: number;
  y: number;
}

// Phases where a ship sits exactly on a body (the engine returns the body's
// position): docked at origin, on layover, or arrived. In-motion / queued /
// wormhole_transit are NOT at-body and keep their own rendering.
export const AT_BODY_PHASES = new Set(['predeparture', 'arrived', 'layover', 'idle']);

// Map bodyId -> the ids of ships sitting on it (within `tol` AU; at rest the match
// is exact, the tolerance just guards float noise). Ships with no body in range are
// omitted. Insertion order of `ships` is preserved within each group.
export function atBodyGroups(
  ships: Located[],
  bodies: Located[],
  tol = 0.05
): Map<string, string[]> {
  const groups = new Map<string, string[]>();
  for (const s of ships) {
    let best: string | null = null;
    let bestD2 = tol * tol;
    for (const b of bodies) {
      const dx = s.x - b.x;
      const dy = s.y - b.y;
      const d2 = dx * dx + dy * dy;
      if (d2 <= bestD2) {
        bestD2 = d2;
        best = b.id;
      }
    }
    if (best !== null) {
      const g = groups.get(best);
      if (g) g.push(s.id);
      else groups.set(best, [s.id]);
    }
  }
  return groups;
}
