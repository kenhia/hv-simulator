import { describe, expect, it } from 'vitest';
import type { FleetEntry } from './api';
import { boardFilter, isFilterActive, nationsPresent, NO_FILTER } from './board';

const e = (transponder: string, phase: string): FleetEntry => ({
  transponder,
  ship: transponder,
  phase,
  system: null,
  eta: null,
  percent_complete: null,
  queue_position: null
});

const roster: FleetEntry[] = [
  e('347.1.1', 'transit'), // Manticore
  e('347.2.3', 'arrived'), // Manticore, arrived
  e('618.1.4', 'hyper_cruise'), // Haven
  e('1.2.2', 'arrived') // Solarian, arrived
];

describe('nationsPresent', () => {
  it('lists distinct nation codes, numeric-sorted', () => {
    expect(nationsPresent(roster)).toEqual(['1', '347', '618']);
  });
});

describe('boardFilter', () => {
  it('no filter shows everything', () => {
    expect(boardFilter(roster, NO_FILTER)).toHaveLength(4);
  });
  it('hideArrived drops arrived ships', () => {
    const r = boardFilter(roster, { hideArrived: true, nations: new Set() });
    expect(r.map((x) => x.transponder)).toEqual(['347.1.1', '618.1.4']);
  });
  it('nation set keeps only those nations (empty = all)', () => {
    const r = boardFilter(roster, { hideArrived: false, nations: new Set(['618']) });
    expect(r.map((x) => x.transponder)).toEqual(['618.1.4']);
  });
  it('combines hideArrived + nations', () => {
    const r = boardFilter(roster, { hideArrived: true, nations: new Set(['347', '1']) });
    expect(r.map((x) => x.transponder)).toEqual(['347.1.1']); // 347.2.3 arrived, 1.2.2 arrived
  });
});

describe('isFilterActive', () => {
  it('is false only with no constraints', () => {
    expect(isFilterActive(NO_FILTER)).toBe(false);
    expect(isFilterActive({ hideArrived: true, nations: new Set() })).toBe(true);
    expect(isFilterActive({ hideArrived: false, nations: new Set(['1']) })).toBe(true);
  });
});
