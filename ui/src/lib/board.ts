// Pure Fleet Board filtering (Sprint 032). Kept out of the component for testing.

import type { FleetEntry } from './api';

export interface BoardFilter {
  hideArrived: boolean;
  nations: Set<string>; // nation codes to SHOW; empty set => show all
}

export const NO_FILTER: BoardFilter = { hideArrived: false, nations: new Set() };

// The nation code of an entry (first transponder component).
export function nationOf(e: FleetEntry): string {
  return e.transponder.split('.')[0];
}

// Distinct nation codes present in the roster, sorted (numeric where possible).
export function nationsPresent(roster: FleetEntry[]): string[] {
  return [...new Set(roster.map(nationOf))].sort((a, b) => Number(a) - Number(b));
}

// Apply the board filter: drop arrived ships (optional) and any nation not in the
// show-set (an empty show-set means "all nations").
export function boardFilter(roster: FleetEntry[], f: BoardFilter): FleetEntry[] {
  return roster.filter((e) => {
    if (f.hideArrived && e.phase === 'arrived') return false;
    if (f.nations.size > 0 && !f.nations.has(nationOf(e))) return false;
    return true;
  });
}

export function isFilterActive(f: BoardFilter): boolean {
  return f.hideArrived || f.nations.size > 0;
}
