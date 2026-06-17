<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchSystemBodies,
    fetchSystemPlaces,
    type Place,
    type SystemBody,
    type SystemDetail
  } from './api';
  import {
    fit,
    panBy,
    screenDist2,
    worldToScreen,
    zoomAbout,
    type Camera,
    type Vec2
  } from './camera';
  import { bodyRows, placeRows, systemDetailRows, type Detail } from './detail';

  export interface SystemSummary {
    planets: number;
    moons: number;
    stations: number;
  }

  let {
    systemId,
    detail = null,
    zoneMode = false,
    fitSignal = 0,
    onselect,
    onexit,
    onsummary
  }: {
    systemId: string;
    detail?: SystemDetail | null;
    zoneMode?: boolean;
    fitSignal?: number;
    onselect?: (d: Detail, bodyName: string | null) => void;
    onexit?: () => void;
    onsummary?: (s: SystemSummary) => void;
  } = $props();

  let wrap: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let width = $state(800);
  let height = $state(600);
  let cam = $state<Camera>({ cx: 0, cy: 0, scale: 1 });
  let bodies = $state<SystemBody[]>([]);
  let places = $state<Place[]>([]);
  let fitScale = 1; // baseline from the initial fit; zooming far below it exits
  let fitted = false;

  const NODE_R = 3;
  const HIT_PX = 14;
  const ringAu = $derived(detail?.primary_hyper_limit_au ?? null);

  function bodyWorld(b: SystemBody): Vec2 {
    return { x: b.position.au.x, y: b.position.au.y };
  }
  // A place rides on a body -> its on-screen point is that body's position.
  function placeWorld(p: Place): Vec2 | null {
    return p.position ? { x: p.position.au.x, y: p.position.au.y } : null;
  }

  function starLabel(): string {
    const primary = detail?.stars?.[0]?.name;
    return primary ?? detail?.name ?? systemId;
  }

  async function load() {
    const [b, p] = await Promise.all([
      fetchSystemBodies(systemId),
      fetchSystemPlaces(systemId).catch(() => [])
    ]);
    bodies = b;
    places = p;
    onsummary?.({
      planets: b.filter((x) => x.type === 'planet').length,
      moons: b.filter((x) => x.type === 'moon').length,
      stations: p.length
    });
    if (!fitted && width > 1) doFit(); // frame the system once its bodies arrive
  }

  function doFit() {
    const pts = bodies.map(bodyWorld);
    if (ringAu) pts.push({ x: ringAu, y: 0 }, { x: -ringAu, y: 0 }); // keep the ring in frame
    cam = pts.length ? fit(pts, width, height) : { cx: 0, cy: 0, scale: 40 };
    fitScale = cam.scale;
    fitted = true;
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

    const origin = worldToScreen({ x: 0, y: 0 }, cam, width, height);

    // Hyper-limit ring around the primary star.
    if (ringAu) {
      ctx.strokeStyle = '#3a5a44';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(origin.x, origin.y, ringAu * cam.scale, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.font = '11px ui-monospace, monospace';
    ctx.textBaseline = 'middle';

    // Primary star at the origin, labelled. (Binary companion placement at its
    // real barycenter offset is deferred — see the system-geometry follow-up.)
    ctx.fillStyle = '#ffd86b';
    ctx.beginPath();
    ctx.arc(origin.x, origin.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#cabf7a';
    ctx.fillText(starLabel(), origin.x + 9, origin.y);

    // Planets / moons.
    for (const b of bodies) {
      const p = worldToScreen(bodyWorld(b), cam, width, height);
      const moon = b.type === 'moon';
      ctx.fillStyle = moon ? '#9aa6bd' : '#cfe0ff';
      ctx.beginPath();
      ctx.arc(p.x, p.y, moon ? NODE_R - 1 : NODE_R, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#8da2c0';
      ctx.fillText(b.name, p.x + NODE_R + 4, p.y);
    }

    // Stations / forts that ride a body (square markers offset from the body).
    ctx.fillStyle = '#caa64a';
    for (const pl of places) {
      const w = placeWorld(pl);
      if (!w) continue;
      const p = worldToScreen(w, cam, width, height);
      ctx.fillRect(p.x - 2, p.y - 6, 4, 4);
    }
  }

  function nearest(sx: number, sy: number): (() => void) | null {
    let best: (() => void) | null = null;
    let bestD = HIT_PX * HIT_PX;
    const consider = (w: Vec2, make: () => void) => {
      const p = worldToScreen(w, cam, width, height);
      const d = screenDist2({ x: sx, y: sy }, p);
      if (d < bestD) {
        bestD = d;
        best = make;
      }
    };
    for (const b of bodies) consider(bodyWorld(b), () => onselect?.(bodyRows(b), b.name));
    for (const pl of places) {
      const w = placeWorld(pl);
      if (w) consider(w, () => onselect?.(placeRows(pl), pl.name ?? null));
    }
    const d = detail;
    if (d) consider({ x: 0, y: 0 }, () => onselect?.(systemDetailRows(d), null));
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
      hit?.();
    }
  }
  function onwheel(e: WheelEvent) {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
    const next = zoomAbout(cam, e.offsetX, e.offsetY, factor, width, height);
    // Zoom-out past the framing scale backs out to the galaxy (unless zone-locked).
    if (!zoneMode && next.scale < fitScale * 0.45) {
      onexit?.();
      return;
    }
    cam = zoneMode ? { ...next, scale: Math.max(next.scale, fitScale * 0.5) } : next;
  }

  onMount(() => {
    const ro = new ResizeObserver(() => resize());
    ro.observe(wrap);
    resize();
    load();
    const poll = setInterval(load, 5000);
    return () => {
      ro.disconnect();
      clearInterval(poll);
    };
  });

  let lastFit = 0;
  $effect(() => {
    if (fitSignal !== lastFit) {
      lastFit = fitSignal;
      doFit();
    }
  });

  $effect(() => {
    void [bodies, places, cam, width, height, ringAu, detail];
    draw();
  });
</script>

<div class="map" bind:this={wrap}>
  <canvas bind:this={canvas} {onpointerdown} {onpointermove} {onpointerup} {onwheel}></canvas>
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
