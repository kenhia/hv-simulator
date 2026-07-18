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

// --- Sort (Sprint 036, #81) -------------------------------------------------

export type SortMode = 'transponder' | 'full-name' | 'ship-name' | 'filed';

export const SORT_ROWS: [SortMode, string][] = [
  ['transponder', 'transponder'],
  ['full-name', 'full name'],
  ['ship-name', 'ship name'],
  ['filed', 'file time (newest)']
];

// The ship name without its prefix (a leading ALL-CAPS token like ATV / PNS / HMS):
// "ATV Phoenix" -> "Phoenix", "PNS Rash al-Din" -> "Rash al-Din".
export function nameWithoutPrefix(ship: string): string {
  const m = ship.match(/^([A-Z]{2,5})\s+(.+)$/);
  return m ? m[2] : ship;
}

// Transponder as a numeric tuple so 42.1.10 sorts after 42.1.9 (not lexically).
function tpKey(tp: string): number[] {
  return tp.split('.').map((n) => Number(n) || 0);
}

function cmpNumArr(a: number[], b: number[]): number {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const d = (a[i] ?? 0) - (b[i] ?? 0);
    if (d) return d;
  }
  return 0;
}

// Sort a (already-filtered) roster. Stable; filed = newest-first (nulls last).
export function boardSort(roster: FleetEntry[], mode: SortMode): FleetEntry[] {
  const r = [...roster];
  if (mode === 'transponder') {
    r.sort((a, b) => cmpNumArr(tpKey(a.transponder), tpKey(b.transponder)));
  } else if (mode === 'full-name') {
    r.sort((a, b) => a.ship.localeCompare(b.ship));
  } else if (mode === 'ship-name') {
    r.sort((a, b) => nameWithoutPrefix(a.ship).localeCompare(nameWithoutPrefix(b.ship)));
  } else if (mode === 'filed') {
    r.sort((a, b) => (b.filed_at ?? '').localeCompare(a.filed_at ?? '')); // newest first
  }
  return r;
}
