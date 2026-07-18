import { describe, expect, it } from 'vitest';
import type { FleetEntry } from './api';
import {
  boardFilter,
  boardSort,
  isFilterActive,
  nameWithoutPrefix,
  nationsPresent,
  NO_FILTER
} from './board';

const e = (transponder: string, phase: string, ship?: string, filed_at?: string): FleetEntry => ({
  transponder,
  ship: ship ?? transponder,
  phase,
  system: null,
  eta: null,
  percent_complete: null,
  queue_position: null,
  filed_at: filed_at ?? null
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

describe('nameWithoutPrefix', () => {
  it('strips a leading ALL-CAPS prefix token', () => {
    expect(nameWithoutPrefix('ATV Phoenix')).toBe('Phoenix');
    expect(nameWithoutPrefix('PNS Rash al-Din')).toBe('Rash al-Din');
    expect(nameWithoutPrefix('Naked')).toBe('Naked'); // no prefix
  });
});

describe('boardSort', () => {
  it('transponder: numeric per component (10 after 9)', () => {
    const r = boardSort([e('42.1.10', 'x'), e('42.1.9', 'x'), e('1.2.2', 'x')], 'transponder');
    expect(r.map((x) => x.transponder)).toEqual(['1.2.2', '42.1.9', '42.1.10']);
  });
  it('full name vs ship name (prefix)', () => {
    const roster = [e('2', 'x', 'PNS Barbarossa'), e('1', 'x', 'ATV Phoenix')];
    expect(boardSort(roster, 'full-name').map((x) => x.ship)).toEqual([
      'ATV Phoenix',
      'PNS Barbarossa'
    ]);
    // by ship name without prefix: Barbarossa < Phoenix
    expect(boardSort(roster, 'ship-name').map((x) => x.ship)).toEqual([
      'PNS Barbarossa',
      'ATV Phoenix'
    ]);
  });
  it('filed: newest first, nulls last', () => {
    const r = boardSort(
      [
        e('a', 'x', 'a', '2026-06-01T00:00:00Z'),
        e('b', 'x', 'b', '2026-06-03T00:00:00Z'),
        e('c', 'x', 'c') // no filed_at
      ],
      'filed'
    );
    expect(r.map((x) => x.transponder)).toEqual(['b', 'a', 'c']);
  });
});
