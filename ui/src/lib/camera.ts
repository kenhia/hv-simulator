// Pure 2D camera + projection between the galactic frame (light-years) and the
// screen (pixels). No DOM, no Svelte — unit-testable in isolation. Screen y grows
// downward, world y grows upward, so the projection flips y.

export interface Vec2 {
  x: number;
  y: number;
}

export interface Camera {
  cx: number; // world-space center (ly)
  cy: number;
  scale: number; // pixels per ly
}

export function worldToScreen(p: Vec2, cam: Camera, width: number, height: number): Vec2 {
  return {
    x: width / 2 + (p.x - cam.cx) * cam.scale,
    y: height / 2 - (p.y - cam.cy) * cam.scale
  };
}

export function screenToWorld(s: Vec2, cam: Camera, width: number, height: number): Vec2 {
  return {
    x: cam.cx + (s.x - width / 2) / cam.scale,
    y: cam.cy - (s.y - height / 2) / cam.scale
  };
}

// Drag-pan: as the pointer moves by (dx, dy) px, the world under it follows.
export function panBy(cam: Camera, dx: number, dy: number): Camera {
  return { ...cam, cx: cam.cx - dx / cam.scale, cy: cam.cy + dy / cam.scale };
}

// Zoom by `factor` about a screen point, keeping the world point under it fixed.
export function zoomAbout(
  cam: Camera,
  sx: number,
  sy: number,
  factor: number,
  width: number,
  height: number
): Camera {
  const w = screenToWorld({ x: sx, y: sy }, cam, width, height);
  const scale = cam.scale * factor;
  return {
    scale,
    cx: w.x - (sx - width / 2) / scale,
    cy: w.y - (height / 2 - sy) / scale
  };
}

// A camera that frames `points` within the viewport (with px padding). Falls back
// to a sane default when there are no points or zero span.
export function fit(points: Vec2[], width: number, height: number, padding = 60): Camera {
  if (points.length === 0) return { cx: 0, cy: 0, scale: 1 };
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const p of points) {
    minX = Math.min(minX, p.x);
    maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y);
    maxY = Math.max(maxY, p.y);
  }
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  const scale = Math.min((width - 2 * padding) / spanX, (height - 2 * padding) / spanY);
  return { cx: (minX + maxX) / 2, cy: (minY + maxY) / 2, scale: scale > 0 ? scale : 1 };
}

// Centre the view on a world point, showing `span` world-units across the smaller
// viewport dimension. Used by Locate-ship (Sprint 031) to frame a chosen ship at a
// fixed zoom regardless of resolution.
export function centerOn(world: Vec2, span: number, width: number, height: number): Camera {
  const scale = Math.min(width, height) / (span > 0 ? span : 1);
  return { cx: world.x, cy: world.y, scale: scale > 0 ? scale : 1 };
}

// Squared screen distance — for nearest-node hit-testing.
export function screenDist2(a: Vec2, b: Vec2): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return dx * dx + dy * dy;
}
