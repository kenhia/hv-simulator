import { describe, expect, it } from 'vitest';
import { fit, panBy, screenToWorld, worldToScreen, zoomAbout, type Camera } from './camera';

const W = 800;
const H = 600;
const cam: Camera = { cx: 10, cy: -5, scale: 4 };

describe('projection', () => {
  it('round-trips world -> screen -> world', () => {
    const p = { x: 42, y: -17 };
    const s = worldToScreen(p, cam, W, H);
    const back = screenToWorld(s, cam, W, H);
    expect(back.x).toBeCloseTo(p.x, 9);
    expect(back.y).toBeCloseTo(p.y, 9);
  });

  it('puts the camera center at the viewport center', () => {
    const s = worldToScreen({ x: cam.cx, y: cam.cy }, cam, W, H);
    expect(s.x).toBeCloseTo(W / 2, 9);
    expect(s.y).toBeCloseTo(H / 2, 9);
  });

  it('flips y (world up = screen up)', () => {
    const below = worldToScreen({ x: cam.cx, y: cam.cy - 1 }, cam, W, H);
    expect(below.y).toBeGreaterThan(H / 2); // smaller world y -> lower on screen
  });
});

describe('pan', () => {
  it('keeps the world point under a dragged pointer fixed', () => {
    const moved = panBy(cam, 40, -25);
    // dragging right by 40px shifts the view: the same screen point now reads a
    // world point 40/scale ly to the left of center.
    expect(moved.cx).toBeCloseTo(cam.cx - 40 / cam.scale, 9);
    expect(moved.cy).toBeCloseTo(cam.cy + -25 / cam.scale, 9);
  });
});

describe('zoom', () => {
  it('keeps the world point under the cursor fixed', () => {
    const sx = 120;
    const sy = 480;
    const before = screenToWorld({ x: sx, y: sy }, cam, W, H);
    const zoomed = zoomAbout(cam, sx, sy, 1.5, W, H);
    const after = screenToWorld({ x: sx, y: sy }, zoomed, W, H);
    expect(after.x).toBeCloseTo(before.x, 9);
    expect(after.y).toBeCloseTo(before.y, 9);
    expect(zoomed.scale).toBeCloseTo(cam.scale * 1.5, 9);
  });
});

describe('fit', () => {
  it('centers on the bounding box of the points', () => {
    const pts = [
      { x: 0, y: 0 },
      { x: 20, y: 10 }
    ];
    const c = fit(pts, W, H, 0);
    expect(c.cx).toBeCloseTo(10, 9);
    expect(c.cy).toBeCloseTo(5, 9);
    expect(c.scale).toBeGreaterThan(0);
  });

  it('is defensive about empty input', () => {
    expect(fit([], W, H).scale).toBe(1);
  });
});
