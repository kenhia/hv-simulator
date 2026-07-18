import { describe, expect, it } from 'vitest';
import type { RouteSegment } from './api';
import { legDurationS, legLabel, legProgress, splitLegs } from './timeline';

const seg = (kind: string, duration_seconds: number, body: string | null = null): RouteSegment => ({
  seq: 0,
  kind,
  t_start: '',
  t_end: '',
  duration_seconds,
  duration_human: '',
  body
});

// Earth -> Mars (layover) -> Earth: two legs.
const segments: RouteSegment[] = [
  seg('transit', 100, 'sol'),
  seg('layover', 20, 'mars'),
  seg('transit', 80, 'sol'),
  seg('layover', 10, 'earth')
];

describe('splitLegs', () => {
  it('splits at each layover (inclusive); final travel with no layover is its own leg', () => {
    const legs = splitLegs(segments);
    expect(legs.map((l) => l.map((s) => s.kind))).toEqual([
      ['transit', 'layover'],
      ['transit', 'layover']
    ]);
    const trailing = splitLegs([
      seg('transit', 50, 'a'),
      seg('layover', 5, 'a'),
      seg('hyper_cruise', 90, 'b')
    ]);
    expect(trailing).toHaveLength(2);
    expect(trailing[1].map((s) => s.kind)).toEqual(['hyper_cruise']);
  });
  it('single-destination route is one leg', () => {
    expect(splitLegs([seg('transit', 100, 'mars')])).toHaveLength(1);
  });
});

describe('legDurationS / legLabel', () => {
  it('sums durations and labels by the layover body (else last body)', () => {
    const legs = splitLegs(segments);
    expect(legDurationS(legs[0])).toBe(120);
    expect(legLabel(legs[0])).toBe('mars');
    expect(legLabel(legs[1])).toBe('earth');
  });
});

describe('legProgress', () => {
  it('maps overall percent to the active leg + local progress', () => {
    const legs = splitLegs(segments); // durations 120, 90; total 210
    expect(legProgress(legs, 0).index).toBe(0);
    expect(legProgress(legs, 0.5)).toEqual({ index: 0, local: 105 / 120 }); // 0.5*210=105 into leg 0 (120)
    const p = legProgress(legs, 0.8); // 168 -> leg1, 48 into 90
    expect(p.index).toBe(1);
    expect(p.local).toBeCloseTo(48 / 90, 6);
  });
});
