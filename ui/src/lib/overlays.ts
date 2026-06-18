// Shared canvas overlays drawn on both maps (Sprint 029). Kept separate from the
// pure scalebar.ts (which has no canvas dependency) and reused by GalaxyMap +
// SystemMap so the bar looks identical in both scenes.

import type { Vec2 } from './camera';
import { scaleBar, type BaseUnit } from './scalebar';

const LABEL_FONT = '11px ui-monospace, monospace';

// True if `cursor` is over a node's text label, so the label is a click target
// too (not just the dot). The label is drawn to the right of `anchor`; the box
// spans from the anchor (covering the small gap) to past the measured text.
export function labelHit(
  cursor: Vec2,
  anchor: Vec2,
  text: string,
  ctx: CanvasRenderingContext2D
): boolean {
  if (!text) return false;
  ctx.font = LABEL_FONT;
  const w = ctx.measureText(text).width;
  const h = 13;
  return (
    cursor.x >= anchor.x &&
    cursor.x <= anchor.x + w + 8 &&
    cursor.y >= anchor.y - h / 2 &&
    cursor.y <= anchor.y + h / 2
  );
}

// A labelled scale bar, bottom-centre (the bottom-left holds the keyboard hints and
// the bottom-right the layers/legend column). `scale` = px per `baseUnit` (ly
// galaxy, au system); the helper picks the unit + a nice round length for the zoom.
export function drawScaleBar(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  scale: number,
  baseUnit: BaseUnit
): void {
  if (!Number.isFinite(scale) || scale <= 0) return;
  const bar = scaleBar(scale, baseUnit);
  if (!Number.isFinite(bar.pixels) || bar.pixels <= 0) return;

  const x0 = Math.round((width - bar.pixels) / 2);
  const y = height - 18;
  const x1 = x0 + bar.pixels;
  ctx.save();
  ctx.strokeStyle = '#9aa6bd';
  ctx.fillStyle = '#9aa6bd';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x0, y - 4);
  ctx.lineTo(x0, y); // left tick
  ctx.lineTo(x1, y); // bar
  ctx.lineTo(x1, y - 4); // right tick
  ctx.stroke();
  ctx.font = '11px ui-monospace, monospace';
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'center';
  ctx.fillText(bar.label, (x0 + x1) / 2, y - 7);
  ctx.restore();
}
