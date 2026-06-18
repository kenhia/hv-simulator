// Pure helper for an adaptive map scale bar (Sprint 029). The camera's `scale`
// is pixels per world-unit — ly in the galaxy scene, AU in the system scene. We
// turn a target on-screen length into a "nice" round distance, choosing the unit
// that keeps the number in a readable 1-3 digit range as the zoom changes:
//   galaxy: light-years
//   system: AU -> light-minutes -> light-seconds -> km (zooming in)
// Kept out of the components for testing, like camera.ts / planner.ts.

export type BaseUnit = 'ly' | 'au';

// Metres per unit (matches the engine constants).
const M_PER: Record<string, number> = {
  km: 1e3,
  ls: 2.99792458e8, // light-second
  lmin: 1.798754748e10, // light-minute
  lhr: 1.0792528488e12, // light-hour (60 light-minutes)
  au: 1.495978707e11,
  ly: 9.4607304725808e15
};

const LABEL: Record<string, string> = {
  km: 'km',
  ls: 'light-sec',
  lmin: 'light-min',
  lhr: 'light-hr',
  au: 'AU',
  ly: 'ly'
};

// Unit ladder per scene, largest first (we pick the largest unit that still gives
// a value >= 1, so the displayed number stays small and readable). The galaxy
// ladder steps down to light-hours/minutes for a deep (locked) zoom on a ship.
const LADDER: Record<BaseUnit, string[]> = {
  ly: ['ly', 'lhr', 'lmin'],
  au: ['au', 'lmin', 'ls', 'km']
};

export interface ScaleBar {
  pixels: number; // on-screen length of the bar
  label: string; // e.g. "5 AU", "30 light-min", "2 ly"
  value: number; // the nice round magnitude
  unit: string; // the chosen unit key
}

// Snap down to a "nice" 1 / 2 / 5 x 10^n number <= x.
function niceNumber(x: number): number {
  if (x <= 0) return 0;
  const mag = Math.pow(10, Math.floor(Math.log10(x)));
  const frac = x / mag;
  const nice = frac >= 5 ? 5 : frac >= 2 ? 2 : 1;
  return nice * mag;
}

// Format the magnitude without trailing-zero noise (0.2, 5, 30, 1.5).
function fmt(v: number): string {
  return Number.isInteger(v) ? String(v) : String(Number(v.toFixed(3)));
}

// Compute the scale bar for the current zoom. `scale` = px per `baseUnit`;
// `targetPx` is the desired bar width (the result is <= this, snapped down).
export function scaleBar(scale: number, baseUnit: BaseUnit, targetPx = 90): ScaleBar {
  const targetMeters = (targetPx / scale) * M_PER[baseUnit];
  const ladder = LADDER[baseUnit];
  // Largest unit whose value is >= 1; fall back to the smallest.
  let unit = ladder[ladder.length - 1];
  for (const u of ladder) {
    if (targetMeters / M_PER[u] >= 1) {
      unit = u;
      break;
    }
  }
  const value = niceNumber(targetMeters / M_PER[unit]);
  const pixels = ((value * M_PER[unit]) / M_PER[baseUnit]) * scale;
  return { pixels, label: `${fmt(value)} ${LABEL[unit]}`, value, unit };
}
