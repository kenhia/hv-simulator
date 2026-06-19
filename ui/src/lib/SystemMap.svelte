<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchSystemBodies,
    fetchSystemPlaces,
    type Junction,
    type Place,
    type SystemBody,
    type SystemDetail,
    type WormholeLink
  } from './api';
  import {
    centerOn,
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
  import { AT_BODY_PHASES, atBodyGroups } from './atbody';
  import { drawScaleBar, labelHit } from './overlays';
  import { bodyColor, starColors, starWorld } from './stars';

  export interface SystemSummary {
    planets: number;
    moons: number;
    stations: number;
  }

  let {
    systemId,
    detail = null,
    junctions = [],
    links = [],
    zoneMode = false,
    fitSignal = 0,
    focus = null,
    focusSignal = 0,
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
    links?: WormholeLink[];
    zoneMode?: boolean;
    fitSignal?: number;
    focus?: { x: number; y: number; span: number } | null; // Locate-ship target (AU)
    focusSignal?: number;
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
  let lastFocus = 0; // the focusSignal already consumed — Locate is one-shot, not per-poll

  const NODE_R = 3;
  const HIT_PX = 14;
  const NEXUS_AU = 50; // fabricated nexus radius (≈ Manticore's canon 7 light-hours)
  const ringAu = $derived(detail?.primary_hyper_limit_au ?? null);
  const stars = $derived(detail?.stars ?? []);
  const starColorMap = $derived(starColors(stars));

  // Wormhole markers in this system: the junctions it *hosts* (the nexus, ⚲) plus
  // the *termini* of junctions that land here (⇄, leading back to a junction in
  // another system). Both open the host junction's queue panel; a terminus shares
  // the host's queue. Fabricated positions (canon gives a radius, not a bearing).
  interface JunctionMarker {
    junctionId: string;
    label: string;
    host: boolean;
    world: Vec2;
  }
  const markers = $derived.by((): JunctionMarker[] => {
    const jName = new Map(junctions.map((j) => [j.id, j.name]));
    const out: Omit<JunctionMarker, 'world'>[] = [];
    for (const j of junctions) {
      if (j.host_system_id === systemId)
        out.push({ junctionId: j.id, label: `⚲ ${j.name}`, host: true });
    }
    for (const l of links) {
      if (l.transit !== 'instant' || l.to_system_id !== systemId || !l.junction_id) continue;
      out.push({
        junctionId: l.junction_id,
        label: `⇄ ${jName.get(l.junction_id) ?? l.junction_id}`,
        host: false
      });
    }
    return out.map((m, i) => ({ ...m, world: nexusWorld(i) }));
  });

  // Fabricated in-system nexus point (canon gives a radius, not a bearing): place
  // markers on distinct bearings at NEXUS_AU.
  function nexusWorld(i: number): Vec2 {
    const a = i * 0.7; // first one "north" (+y = up), then fan out
    return { x: NEXUS_AU * Math.sin(a), y: NEXUS_AU * Math.cos(a) };
  }

  function bodyWorld(b: SystemBody): Vec2 {
    return { x: b.position.au.x, y: b.position.au.y };
  }
  // The primary star's in-system point (origin if positions aren't available) —
  // the hyper-limit ring centres here, not on the (empty) barycenter.
  function primaryWorld(): Vec2 {
    return stars[0] ? starWorld(stars[0]) : { x: 0, y: 0 };
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
    // Frame the system once its bodies arrive. A *pending* Locate (unconsumed
    // focusSignal) centres on the ship instead; an already-consumed one is left
    // alone so the 5s poll never re-zooms over the user's manual pan/zoom.
    if (width > 1) {
      if (focus && focusSignal !== lastFocus) applyFocus();
      else if (!fitted) doFit();
    }
  }

  function doFit() {
    const pts = bodies.map(bodyWorld);
    stars.forEach((st) => pts.push(starWorld(st))); // keep both binary stars in frame
    const c = primaryWorld();
    if (ringAu) pts.push({ x: c.x + ringAu, y: c.y }, { x: c.x - ringAu, y: c.y }); // ring
    markers.forEach((m) => pts.push(m.world)); // keep nexus/termini in frame
    cam = pts.length ? fit(pts, width, height) : { cx: 0, cy: 0, scale: 40 };
    fitScale = cam.scale;
    fitted = true;
  }

  function applyFocus() {
    if (!focus) return;
    lastFocus = focusSignal; // consume this Locate so it applies exactly once
    cam = centerOn({ x: focus.x, y: focus.y }, focus.span, width, height);
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

    // Hyper-limit ring around the primary star (centred on its real position).
    if (ringAu && layers.ring) {
      const c = worldToScreen(primaryWorld(), cam, width, height);
      ctx.strokeStyle = '#3a5a44';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(c.x, c.y, ringAu * cam.scale, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.font = '11px ui-monospace, monospace';
    ctx.textBaseline = 'middle';

    // Each star at its barycenter offset, labelled (a binary's A/B sit apart; a
    // single star is at the origin). Fall back to one star at origin if no detail.
    if (stars.length) {
      for (const st of stars) {
        const s = worldToScreen(starWorld(st), cam, width, height);
        ctx.fillStyle = starColorMap.get(st.id) ?? '#ffd86b';
        ctx.beginPath();
        ctx.arc(s.x, s.y, 5, 0, Math.PI * 2);
        ctx.fill();
        if (layers.labels) {
          ctx.fillStyle = '#cabf7a';
          ctx.fillText(st.name ?? detail?.name ?? systemId, s.x + 9, s.y);
        }
      }
    } else {
      const o = worldToScreen({ x: 0, y: 0 }, cam, width, height);
      ctx.fillStyle = '#ffd86b';
      ctx.beginPath();
      ctx.arc(o.x, o.y, 5, 0, Math.PI * 2);
      ctx.fill();
      if (layers.labels) {
        ctx.fillStyle = '#cabf7a';
        ctx.fillText(starLabel(), o.x + 9, o.y);
      }
    }

    // Planets / moons, coloured by their parent star so binaries group visibly.
    for (const b of bodies) {
      // Sol's stations (e.g. Titan Station) arrive as `station`-type *bodies* from
      // the JPL delegate — gate them with the stations layer, like ride-on places.
      if (b.type === 'station' && !layers.stations) continue;
      const p = worldToScreen(bodyWorld(b), cam, width, height);
      const moon = b.type === 'moon';
      ctx.fillStyle = bodyColor(b, starColorMap);
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

    // Wormhole markers (fabricated in-system positions): a host nexus (⚲, filled
    // centre) or a terminus to another system's junction (⇄, hollow). The queue-
    // panel interaction target; always drawn.
    markers.forEach((m) => {
      const p = worldToScreen(m.world, cam, width, height);
      ctx.strokeStyle = '#ffcf6b';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.stroke();
      if (m.host) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = '#ffcf6b';
        ctx.fill();
      }
      if (layers.labels) {
        ctx.fillStyle = '#e0c98a';
        ctx.fillText(m.label, p.x + 10, p.y);
      }
    });

    if (layers.ships) drawShips(ctx);
    drawScaleBar(ctx, width, height, cam.scale, 'au');
  }

  // Tracked ships in this system. Ships *at rest at a body* are listed on a leader
  // off the body's label (see drawAtBodyLabels) rather than as overlapping dots;
  // in-motion / queued ships keep their dot + heading vector.
  function drawShips(ctx: CanvasRenderingContext2D) {
    const here = (ships?.() ?? []).filter(
      (s) => s.system === systemId && s.frame === 'heliocentric'
    );
    // At-rest ships grouped onto the body they're parked at.
    const located = here
      .filter((s) => AT_BODY_PHASES.has(s.phase))
      .map((s) => ({ id: s.transponder, x: kmToAu(s.posKm.x), y: kmToAu(s.posKm.y) }));
    const groups = atBodyGroups(
      located,
      bodies.map((b) => ({ id: b.id, x: b.position.au.x, y: b.position.au.y }))
    );
    const grouped = new Set<string>();
    for (const tps of groups.values()) for (const tp of tps) grouped.add(tp);

    for (const sh of here) {
      if (grouped.has(sh.transponder)) continue; // shown on the body's leader instead
      // A queued / transiting ship's reported position is the star centre (the
      // wait position is immaterial); draw it at the junction nexus instead.
      const queued = sh.phase === 'queued' || sh.phase === 'wormhole_transit';
      const at =
        queued && markers.length
          ? markers[0].world
          : { x: kmToAu(sh.posKm.x), y: kmToAu(sh.posKm.y) };
      const p = worldToScreen(at, cam, width, height);
      const speed = queued ? 0 : Math.hypot(sh.velKmS.x, sh.velKmS.y);
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
        const tag =
          queued && sh.queuePosition ? `${sh.transponder} #${sh.queuePosition}` : sh.transponder;
        ctx.fillText(tag, p.x + 6, p.y - 6);
      }
    }
    if (layers.labels) drawAtBodyLabels(ctx, groups);
  }

  // A leader off each occupied body's label: a short vertical line dropped from a
  // small indent just right of the body dot, with the parked ships' transponder
  // codes stacked beside it (in faction colour). Caps a crowd at MAX.
  function drawAtBodyLabels(ctx: CanvasRenderingContext2D, groups: Map<string, string[]>) {
    const MAX = 6;
    const byId = new Map(bodies.map((b) => [b.id, b]));
    for (const [bodyId, tps] of groups) {
      const b = byId.get(bodyId);
      if (!b) continue;
      const p = worldToScreen(bodyWorld(b), cam, width, height);
      const lineX = p.x + 6; // small indent right of the dot, under the label
      const shown = tps.slice(0, MAX);
      const codeX = lineX + 5;
      let y = p.y + 13;
      ctx.strokeStyle = '#5a6b86';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(lineX, p.y + 5);
      ctx.lineTo(lineX, y + (shown.length - 1) * 12 + 1);
      ctx.stroke();
      for (const tp of shown) {
        ctx.fillStyle = factionColor(tp);
        ctx.fillText(tp, codeX, y);
        y += 12;
      }
      if (tps.length > MAX) {
        ctx.fillStyle = '#8da2c0';
        ctx.fillText(`+${tps.length - MAX} more`, codeX, y);
      }
    }
  }

  function nearest(sx: number, sy: number): (() => void) | null {
    let best: (() => void) | null = null;
    let bestD = HIT_PX * HIT_PX;
    const ctx = canvas?.getContext('2d');
    const cursor = { x: sx, y: sy };
    // Hit the node dot, or its text label (labelHit -> treat as a near hit so a dot
    // directly under the cursor still wins, but a label beats empty space).
    const consider = (w: Vec2, make: () => void, label?: string) => {
      const p = worldToScreen(w, cam, width, height);
      let d = screenDist2(cursor, p);
      if (label && ctx && labelHit(cursor, p, label, ctx)) d = Math.min(d, 1);
      if (d < bestD) {
        bestD = d;
        best = make;
      }
    };
    for (const b of bodies) consider(bodyWorld(b), () => onselect?.(bodyRows(b), b.name), b.name);
    for (const pl of places) {
      const w = placeWorld(pl);
      if (w) consider(w, () => onselect?.(placeRows(pl), pl.name ?? null));
    }
    const d = detail;
    // The stars are the system-detail click targets (the barycenter origin is empty
    // in a binary); fall back to the origin when no star positions are available.
    if (d && stars.length) {
      for (const st of stars)
        consider(
          starWorld(st),
          () => onselect?.(systemDetailRows(d), st.name),
          st.name ?? undefined
        );
    } else if (d) {
      consider({ x: 0, y: 0 }, () => onselect?.(systemDetailRows(d), null));
    }
    markers.forEach((m) => consider(m.world, () => onjunction?.(m.junctionId), m.label));
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

  // Locate-ship: centre on the ship when the page bumps focusSignal (same system).
  $effect(() => {
    if (focus && focusSignal !== lastFocus && width > 1) applyFocus();
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
