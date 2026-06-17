import { describe, expect, it } from 'vitest';
import { deadReckon, kmToAu, kmToLy, simNowMs, type SimClockModel } from './live';

describe('simNowMs', () => {
  it('advances at the clock rate from the epochs', () => {
    const c: SimClockModel = { simEpochMs: 1000, realEpochMs: 0, rate: 1 };
    expect(simNowMs(c, 5000)).toBe(6000); // sim_epoch + (wall - real_epoch)*rate
  });
  it('honours an accelerated rate', () => {
    const c: SimClockModel = { simEpochMs: 0, realEpochMs: 0, rate: 60 };
    expect(simNowMs(c, 1000)).toBe(60_000); // 1 real s -> 60 sim s
  });
});

describe('deadReckon', () => {
  it('extrapolates linearly by velocity over elapsed seconds', () => {
    const p = deadReckon(
      { x: 0, y: 0, z: 0 },
      { x: 10, y: -2, z: 0 }, // km/s
      1000,
      3000 // 2 s later
    );
    expect(p).toEqual({ x: 20, y: -4, z: 0 });
  });
});

describe('unit conversions', () => {
  it('km -> ly and km -> AU are in the right ballpark', () => {
    expect(kmToLy(9.4607304725808e12)).toBeCloseTo(1, 9);
    expect(kmToAu(1.495978707e8)).toBeCloseTo(1, 9);
  });
});
