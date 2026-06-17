<script lang="ts">
  import { onMount } from 'svelte';
  import type { Junction, System, WormholeLink } from './api';
  import {
    fit,
    panBy,
    screenDist2,
    worldToScreen,
    zoomAbout,
    type Camera,
    type Vec2
  } from './camera';

  let {
    systems = [],
    links = [],
    junctions = [],
    selectedId = null,
    fitSignal = 0,
    onselect,
    onenter
  }: {
    systems?: System[];
    links?: WormholeLink[];
    junctions?: Junction[];
    selectedId?: string | null;
    fitSignal?: number;
    onselect?: (s: System) => void;
    onenter?: (s: System) => void;
  } = $props();

  let wrap: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let width = $state(800);
  let height = $state(600);
  let cam = $state<Camera>({ cx: 0, cy: 0, scale: 1 });
  let fitted = false;
  let fitScale = 1; // baseline from the initial fit; zooming far past it enters a system

  const placed = $derived(systems.filter((s) => s.coordinates !== null));
  const byId = $derived(new Map(systems.map((s) => [s.id, s])));
  const hostSystems = $derived(new Set(junctions.map((j) => j.host_system_id)));

  const NODE_R = 4;
  const HIT_PX = 14;

  // Top-down view of the galactic plane: X = galactic east (right), Z = galactic
  // north (up). The frame reserves Y (out-of-plane) ~ 0, so we project X-Z.
  function world(s: System): Vec2 {
    return { x: s.coordinates!.x_ly, y: s.coordinates!.z_ly };
  }

  function resize() {
    const r = wrap.getBoundingClientRect();
    width = Math.max(1, Math.floor(r.width));
    height = Math.max(1, Math.floor(r.height));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
  }

  function draw() {
    const ctx = canvas?.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    // Wormhole edges (true wormholes between two placed systems).
    ctx.strokeStyle = '#33476b';
    ctx.lineWidth = 1;
    for (const link of links) {
      if (link.transit !== 'instant' || !link.to_system_id) continue;
      const a = byId.get(link.from_system_id);
      const b = byId.get(link.to_system_id);
      if (!a?.coordinates || !b?.coordinates) continue;
      const pa = worldToScreen(world(a), cam, width, height);
      const pb = worldToScreen(world(b), cam, width, height);
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    }

    // System nodes.
    ctx.font = '11px ui-monospace, monospace';
    ctx.textBaseline = 'middle';
    for (const s of placed) {
      const p = worldToScreen(world(s), cam, width, height);
      const isHost = hostSystems.has(s.id);
      const isSel = s.id === selectedId;

      if (isHost) {
        ctx.strokeStyle = '#caa64a';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(p.x, p.y, NODE_R + 4, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.fillStyle = s.is_binary ? '#9fd0ff' : '#dfe6f0';
      ctx.beginPath();
      ctx.arc(p.x, p.y, NODE_R, 0, Math.PI * 2);
      ctx.fill();
      if (isSel) {
        ctx.strokeStyle = '#ff9d4d';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, NODE_R + 6, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.fillStyle = isSel ? '#ffd9b0' : '#8da2c0';
      ctx.fillText(s.name, p.x + NODE_R + 4, p.y);
    }
  }

  function nearest(sx: number, sy: number, maxPx = HIT_PX): System | null {
    let best: System | null = null;
    let bestD = maxPx * maxPx;
    for (const s of placed) {
      const p = worldToScreen(world(s), cam, width, height);
      const d = screenDist2({ x: sx, y: sy }, p);
      if (d < bestD) {
        bestD = d;
        best = s;
      }
    }
    return best;
  }

  let dragging = false;
  let moved = false;
  let lastX = 0;
  let lastY = 0;

  function onpointerdown(e: PointerEvent) {
    dragging = true;
    moved = false;
    lastX = e.offsetX;
    lastY = e.offsetY;
    canvas.setPointerCapture(e.pointerId);
  }
  function onpointermove(e: PointerEvent) {
    if (!dragging) return;
    const dx = e.offsetX - lastX;
    const dy = e.offsetY - lastY;
    if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
    cam = panBy(cam, dx, dy);
    lastX = e.offsetX;
    lastY = e.offsetY;
  }
  function onpointerup(e: PointerEvent) {
    dragging = false;
    if (!moved) {
      const hit = nearest(e.offsetX, e.offsetY);
      if (hit) onselect?.(hit);
    }
  }
  function onwheel(e: WheelEvent) {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
    const next = zoomAbout(cam, e.offsetX, e.offsetY, factor, width, height);
    // Zooming deep past the framing scale, with a system near centre, drills in.
    if (next.scale > fitScale * 8) {
      const hit = nearest(width / 2, height / 2, 80);
      if (hit) {
        onenter?.(hit);
        return;
      }
    }
    cam = next;
  }

  function ondblclick(e: MouseEvent) {
    const hit = nearest(e.offsetX, e.offsetY);
    if (hit) onenter?.(hit);
  }

  onMount(() => {
    const ro = new ResizeObserver(() => resize());
    ro.observe(wrap);
    resize();
    return () => ro.disconnect();
  });

  // Frame the galaxy once data + a real viewport are available.
  $effect(() => {
    if (!fitted && placed.length > 0 && width > 1) {
      cam = fit(placed.map(world), width, height);
      fitScale = cam.scale;
      fitted = true;
    }
  });

  // `f` (fit/reset): the page bumps fitSignal.
  let lastFit = 0;
  $effect(() => {
    if (fitSignal !== lastFit && placed.length > 0 && width > 1) {
      lastFit = fitSignal;
      cam = fit(placed.map(world), width, height);
      fitScale = cam.scale;
    }
  });

  // Redraw whenever inputs, camera, selection, or size change.
  $effect(() => {
    void [placed, links, hostSystems, cam, selectedId, width, height];
    draw();
  });
</script>

<div class="map" bind:this={wrap}>
  <canvas bind:this={canvas} {onpointerdown} {onpointermove} {onpointerup} {onwheel} {ondblclick}
  ></canvas>
</div>

<style>
  .map {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }
  canvas {
    display: block;
    cursor: grab;
    touch-action: none;
  }
  canvas:active {
    cursor: grabbing;
  }
</style>
