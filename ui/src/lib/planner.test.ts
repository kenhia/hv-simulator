import { describe, expect, it } from 'vitest';
import type { FiledRoute } from './api';
import {
  canPlan,
  CIVILIAN_LAYOVER_S,
  cycleLabel,
  defaultLayoverS,
  isLoop,
  loopWaypoints,
  repeatSpec,
  routeSystems
} from './planner';

describe('defaultLayoverS', () => {
  it('gives civilians a min layover, military none', () => {
    expect(defaultLayoverS(false)).toBe(CIVILIAN_LAYOVER_S);
    expect(defaultLayoverS(true)).toBe(0);
  });
});

describe('canPlan', () => {
  const origin = { system: 'sol', body: 'earth' };
  it('needs ship + origin + complete waypoints', () => {
    expect(
      canPlan('347.5.3', origin, [
        { system: 'manticore', body: 'manticore:manticore', layover_s: 0 }
      ])
    ).toBe(true);
    expect(canPlan('', origin, [{ system: 'manticore', body: 'm', layover_s: 0 }])).toBe(false);
    expect(canPlan('347.5.3', origin, [])).toBe(false);
    expect(canPlan('347.5.3', origin, [{ system: 'manticore', body: '', layover_s: 0 }])).toBe(
      false
    );
  });
});

describe('routeSystems', () => {
  it('lists origin + each leg system, de-duped consecutively', () => {
    const filed: FiledRoute = {
      schema: 'hvsim.filed-route/v1',
      ship: '347.5.3',
      origin: { system: 'sol', body: 'earth' },
      depart_at: '1890-01-01T00:00:00Z',
      legs: [
        { mode: 'hyper', to_system: 'sigma-draconis', to_body: null, layover_s: 0 },
        { mode: 'wormhole', to_system: 'manticore', to_body: null, layover_s: 0 },
        { mode: 'nspace', to_system: 'manticore', to_body: 'manticore:manticore', layover_s: 0 }
      ]
    };
    expect(routeSystems(filed)).toEqual(['sol', 'sigma-draconis', 'manticore']);
  });
});

describe('repeating routes (#59)', () => {
  const filed: FiledRoute = {
    schema: 'hvsim.filed-route/v1',
    ship: '1.1.1',
    origin: { system: 'sol', body: 'earth' },
    depart_at: '1890-01-01T00:00:00+00:00',
    legs: [
      { mode: 'hyper', to_system: 'beowulf', to_body: null, layover_s: 0 },
      { mode: 'nspace', to_system: 'beowulf', to_body: 'beowulf:p1', layover_s: 7200 },
      { mode: 'hyper', to_system: 'sol', to_body: 'earth', layover_s: 7200 }
    ]
  };

  it('closes the itinerary back to the origin', () => {
    const wps = loopWaypoints(
      { system: 'sol', body: 'earth' },
      [{ system: 'beowulf', body: 'beowulf:p1', layover_s: 7200 }],
      7200
    );
    expect(wps.map((w) => w.body)).toEqual(['beowulf:p1', 'earth']);
  });

  it('ranges only the legs that reach a body', () => {
    const spec = repeatSpec(filed, { minLayoverH: 1, maxLayoverH: 4, cycles: null });
    expect(spec.layovers).toEqual([
      { min_s: 0, max_s: 0 },
      { min_s: 3600, max_s: 14400 },
      { min_s: 3600, max_s: 14400 }
    ]);
    expect(spec.cycles).toBeNull();
  });

  it('never lets max fall below min', () => {
    const spec = repeatSpec(filed, { minLayoverH: 6, maxLayoverH: 1, cycles: 3 });
    expect(spec.layovers[2]).toEqual({ min_s: 21600, max_s: 21600 });
    expect(spec.cycles).toBe(3);
  });

  it('recognises a closed loop', () => {
    expect(isLoop(filed)).toBe(true);
    expect(isLoop({ ...filed, legs: filed.legs.slice(0, 2) })).toBe(false);
  });

  it('labels the cycle', () => {
    expect(cycleLabel(3, null)).toBe('cycle 3');
    expect(cycleLabel(3, 5)).toBe('cycle 3 of 5');
    expect(cycleLabel(null, null)).toBe('');
  });
});
