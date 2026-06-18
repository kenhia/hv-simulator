import { describe, expect, it } from 'vitest';
import type { FiledRoute } from './api';
import { canPlan, CIVILIAN_LAYOVER_S, defaultLayoverS, routeSystems } from './planner';

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
