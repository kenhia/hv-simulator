import { describe, expect, it } from 'vitest';
import { scaleBar } from './scalebar';

describe('scaleBar', () => {
  it('galaxy scene reports light-years', () => {
    // scale = px per ly. At 0.5 px/ly a 90px target ~ 180 ly -> nice 100 ly.
    const b = scaleBar(0.5, 'ly');
    expect(b.unit).toBe('ly');
    expect(b.label).toBe('100 ly');
    expect(b.pixels).toBeCloseTo(50, 5); // 100 ly * 0.5 px/ly
  });

  it('system scene uses AU when the span is AU-scale', () => {
    // scale = px per AU. 30 px/AU, 90px target = 3 AU -> nice 2 AU.
    const b = scaleBar(30, 'au');
    expect(b.unit).toBe('au');
    expect(b.label).toBe('2 AU');
    expect(b.pixels).toBeCloseTo(60, 5);
  });

  it('drops to light-minutes when zoomed below ~1 AU', () => {
    // 1 AU = 8.317 light-min. At 500 px/AU, 90px = 0.18 AU = ~1.5 lmin.
    const b = scaleBar(500, 'au');
    expect(b.unit).toBe('lmin');
    expect(b.value).toBeGreaterThanOrEqual(1);
  });

  it('drops to light-seconds, then km, on deep zoom', () => {
    expect(scaleBar(5000, 'au').unit).toBe('ls');
    expect(scaleBar(5e8, 'au').unit).toBe('km');
  });

  it('galaxy scene steps down to light-hours/minutes on a deep (locked) zoom', () => {
    // A galaxy-scale view (a few ly across) stays in ly.
    expect(scaleBar(50, 'ly').unit).toBe('ly');
    // Much deeper: a fraction of a ly reads in light-hours, then light-minutes.
    expect(scaleBar(2e5, 'ly').unit).toBe('lhr');
    expect(scaleBar(1e7, 'ly').unit).toBe('lmin');
  });

  it('snaps to nice 1/2/5 numbers and the bar fits the target', () => {
    for (const scale of [0.3, 1, 7, 42, 300]) {
      const b = scaleBar(scale, 'au', 90);
      const frac = b.value / Math.pow(10, Math.floor(Math.log10(b.value)));
      expect([1, 2, 5]).toContain(Math.round(frac));
      expect(b.pixels).toBeLessThanOrEqual(90 + 1e-6); // snapped down
      expect(b.pixels).toBeGreaterThan(0);
    }
  });
});
