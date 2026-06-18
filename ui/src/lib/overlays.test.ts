import { describe, expect, it } from 'vitest';
import { labelHit } from './overlays';

// Minimal CanvasRenderingContext2D stand-in: labelHit only needs `font` + a
// measureText width. ~7 px/char is close enough to the monospace metric.
const mockCtx = () =>
  ({
    font: '',
    measureText: (t: string) => ({ width: t.length * 7 })
  }) as unknown as CanvasRenderingContext2D;

describe('labelHit', () => {
  const anchor = { x: 100, y: 50 };
  const ctx = mockCtx();

  it('hits over the label text to the right of the anchor', () => {
    // "Manticore" = 9 chars ~ 63px wide; box spans x 100..171, y 43.5..56.5.
    expect(labelHit({ x: 140, y: 50 }, anchor, 'Manticore', ctx)).toBe(true);
    expect(labelHit({ x: 101, y: 47 }, anchor, 'Manticore', ctx)).toBe(true);
  });

  it('misses left of the anchor, far right, or off the line', () => {
    expect(labelHit({ x: 90, y: 50 }, anchor, 'Manticore', ctx)).toBe(false);
    expect(labelHit({ x: 300, y: 50 }, anchor, 'Manticore', ctx)).toBe(false);
    expect(labelHit({ x: 140, y: 80 }, anchor, 'Manticore', ctx)).toBe(false);
  });

  it('empty label never hits', () => {
    expect(labelHit({ x: 100, y: 50 }, anchor, '', ctx)).toBe(false);
  });
});
