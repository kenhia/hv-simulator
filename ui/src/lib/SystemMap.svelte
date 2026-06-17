<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchSystemBodies,
    fetchSystemPlaces,
    type Junction,
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
  import { factionColor } from './factions';
  import { DEFAULT_LAYERS, type Layers } from './layers';
  import { kmToAu, type LiveShip } from './live';

  export interface SystemSummary {
    planets: number;
    moons: number;
    stations: number;
  }

  let {
    systemId,
    detail = null,
    junctions = [],
    zoneMode = false,
    fitSignal = 0,
    ships,
    layers = DEFAULT_LAYERS,
    onselect,
    onexit,
    onsummary,
    onjunction
  }: {
    systemId: string;
    detail?: SystemDetail | null;
    junctions?: Junction[];
    zoneMode?: boolean;
    fitSignal?: number;
    ships?: () => LiveShip[];
    layers?: Layers;
    onselect?: (d: Detail, bodyName: string | null) => void;
    onexit?: () => void;
    onsummary?: (s: SystemSummary) => void;
    onjunction?: (id: string) => void;
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
  const NEXUS_AU = 50; // fabricated nexus radius (≈ Manticore's canon 7 light-hours)
  const ringAu = $derived(detail?.primary_hyper_limit_au ?? null);
  const hostJunctions = $derived(junctions.filter((j) => j.host_system_id === systemId));

  // Fabricated in-system nexus point (canon gives a radius, not a bearing): place
  // junctions on distinct bearings at NEXUS_AU.
  function nexusWorld(i: number): Vec2 {
    const a = i * 0.7; // first one "north" (+y = up), then fan out
    return { x: NEXUS_AU * Math.sin(a), y: NEXUS_AU * Math.cos(a) };
  }

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
    hostJunctions.forEach((_, i) => pts.push(nexusWorld(i))); // keep the nexus in frame
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
    if (ringAu && layers.ring) {
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
    if (layers.labels) {
      ctx.fillStyle = '#cabf7a';
      ctx.fillText(starLabel(), origin.x + 9, origin.y);
    }

    // Planets / moons.
    for (const b of bodies) {
      const p = worldToScreen(bodyWorld(b), cam, width, height);
      const moon = b.type === 'moon';
      ctx.fillStyle = moon ? '#9aa6bd' : '#cfe0ff';
      ctx.beginPath();
      ctx.arc(p.x, p.y, moon ? NODE_R - 1 : NODE_R, 0, Math.PI * 2);
      ctx.fill();
      if (layers.labels) {
        ctx.fillStyle = '#8da2c0';
        ctx.fillText(b.name, p.x + NODE_R + 4, p.y);
      }
    }

    // Stations / forts that ride a body (square markers offset from the body).
    if (layers.stations) {
      ctx.fillStyle = '#caa64a';
      for (const pl of places) {
        const w = placeWorld(pl);
        if (!w) continue;
        const p = worldToScreen(w, cam, width, height);
        ctx.fillRect(p.x - 2, p.y - 6, 4, 4);
      }
    }

    // Wormhole-junction nexus (fabricated in-system position): a gold ring glyph.
    // Always drawn — it's the queue-panel interaction target.
    hostJunctions.forEach((j, i) => {
      const p = worldToScreen(nexusWorld(i), cam, width, height);
      ctx.strokeStyle = '#ffcf6b';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
      ctx.fillStyle = '#ffcf6b';
      ctx.fill();
      if (layers.labels) {
        ctx.fillStyle = '#e0c98a';
        ctx.fillText(`⚲ ${j.name}`, p.x + 10, p.y);
      }
    });

    if (layers.ships) drawShips(ctx);
  }

  // Tracked ships currently in this system: a dot + a short heading vector
  // (fatter dot at rest), at their dead-reckoned heliocentric position (km -> AU).
  function drawShips(ctx: CanvasRenderingContext2D) {
    for (const sh of ships?.() ?? []) {
      if (sh.system !== systemId || sh.frame !== 'heliocentric') continue;
      const p = worldToScreen({ x: kmToAu(sh.posKm.x), y: kmToAu(sh.posKm.y) }, cam, width, height);
      const speed = Math.hypot(sh.velKmS.x, sh.velKmS.y);
      const color = factionColor(sh.transponder);
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      if (speed > 1) {
        const ux = sh.velKmS.x / speed;
        const uy = -sh.velKmS.y / speed; // screen y is down
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x + ux * 12, p.y + uy * 12);
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.arc(p.x, p.y, speed > 1 ? 2.5 : 4, 0, Math.PI * 2);
      ctx.fill();
      if (layers.labels) {
        ctx.fillStyle = color;
        ctx.fillText(sh.transponder, p.x + 6, p.y - 6);
      }
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
    hostJunctions.forEach((j, i) => consider(nexusWorld(i), () => onjunction?.(j.id)));
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
    let raf = 0;
    const loop = () => {
      if (!document.hidden) draw();
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => {
      ro.disconnect();
      clearInterval(poll);
      cancelAnimationFrame(raf);
    };
  });

  let lastFit = 0;
  $effect(() => {
    if (fitSignal !== lastFit) {
      lastFit = fitSignal;
      doFit();
    }
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
