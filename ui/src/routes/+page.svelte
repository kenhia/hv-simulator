<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchGalaxy,
    fetchShipRoute,
    fetchSystemDetail,
    type Galaxy,
    type RouteOut,
    type System,
    type SystemDetail
  } from '$lib/api';
  import { putClock } from '$lib/api';
  import { actionForKey } from '$lib/keymap';
  import { breadcrumb, GALAXY, type Scene } from '$lib/scene';
  import { shipRows, systemRows, type Detail } from '$lib/detail';
  import { DEFAULT_LAYERS, type Layers } from '$lib/layers';
  import { LiveFleet } from '$lib/live';
  import AtAGlance from '$lib/AtAGlance.svelte';
  import DataPanel from '$lib/DataPanel.svelte';
  import FleetBoard from '$lib/FleetBoard.svelte';
  import GalaxyMap from '$lib/GalaxyMap.svelte';
  import HelpOverlay from '$lib/HelpOverlay.svelte';
  import JunctionQueuePanel from '$lib/JunctionQueuePanel.svelte';
  import LayersPanel from '$lib/LayersPanel.svelte';
  import Legend from '$lib/Legend.svelte';
  import SystemMap from '$lib/SystemMap.svelte';
  import TimeScrubber from '$lib/TimeScrubber.svelte';

  let galaxy = $state<Galaxy>({ systems: [], links: [], junctions: [] });
  let error = $state<string | null>(null);
  let loading = $state(true);

  let scene = $state<Scene>(GALAXY);
  let selectedSystem = $state<System | null>(null);
  let systemDetail = $state<SystemDetail | null>(null);
  let panel = $state<Detail | null>(null);
  let focusedBody = $state<string | null>(null);
  let zoneMode = $state(false);
  let fitSignal = $state(0);
  let summary = $state<{ planets: number; moons: number; stations: number } | null>(null);

  // Live fleet (created eagerly so the maps' render loop can read it on frame 1).
  const live = new LiveFleet();
  let roster = $state(live.roster);
  let tracked = $state(new Set<string>());
  let selectedShip = $state<string | null>(null);
  let selectedRoute = $state<RouteOut | null>(null);
  let junctionQueueId = $state<string | null>(null);
  const ships = () => live.ships();

  let layers = $state<Layers>({ ...DEFAULT_LAYERS });
  let showHelp = $state(false);
  let showLayers = $state(false);
  let dev = $state(false); // /clock dev_controls_enabled -> show the time scrubber
  let clockRate = $state(1);
  let scrubRate = $state(3600);

  function toggleLayer(key: keyof Layers) {
    layers = { ...layers, [key]: !layers[key] };
  }
  async function scrubPut(body: { rate?: number; jump_to?: string; advance_seconds?: number }) {
    try {
      await putClock(body);
      await live.resyncClock();
    } catch {
      /* clock controls disabled (prod) — ignore */
    }
  }
  const togglePlay = () => scrubPut({ rate: clockRate > 0 ? 0 : scrubRate });
  const stepClock = (seconds: number) => scrubPut({ advance_seconds: seconds });
  function setScrubRate(r: number) {
    scrubRate = r;
    if (clockRate > 0) scrubPut({ rate: r });
  }
  const jumpNow = () => scrubPut({ jump_to: new Date().toISOString() });

  const placed = $derived(galaxy.systems.filter((s) => s.coordinates !== null).length);
  const stubbed = $derived(galaxy.systems.length - placed);
  const linkCount = $derived(
    galaxy.links.filter((l) => l.transit === 'instant' && l.to_system_id !== null).length
  );
  const systemId = $derived(scene.kind === 'system' ? scene.id : null);
  const crumb = $derived(breadcrumb(scene, systemDetail?.name ?? null, focusedBody));

  async function enterSystem(s: System) {
    selectedSystem = s;
    panel = null;
    focusedBody = null;
    zoneMode = false;
    summary = null;
    selectedShip = null;
    selectedRoute = null;
    junctionQueueId = null;
    try {
      systemDetail = await fetchSystemDetail(s.id);
    } catch {
      systemDetail = null;
    }
    scene = { kind: 'system', id: s.id };
  }

  function exitToGalaxy() {
    scene = GALAXY;
    systemDetail = null;
    focusedBody = null;
    panel = null;
    selectedShip = null;
    selectedRoute = null;
    junctionQueueId = null;
  }

  function openQueue(id: string) {
    panel = null; // one right-side panel at a time
    junctionQueueId = id;
  }

  async function selectShip(tp: string) {
    const entry = roster.find((e) => e.transponder === tp);
    if (!entry) return;
    junctionQueueId = null;
    // Fly to it: into its system, or out to the galaxy if it's in hyper.
    if (entry.system) {
      const sys = galaxy.systems.find((s) => s.id === entry.system);
      if (sys && !(scene.kind === 'system' && scene.id === sys.id)) await enterSystem(sys);
    } else if (scene.kind === 'system') {
      exitToGalaxy();
    }
    selectedShip = tp;
    panel = shipRows(entry);
    selectedRoute = null;
    try {
      selectedRoute = await fetchShipRoute(tp);
    } catch {
      selectedRoute = null;
    }
  }

  function toggleTrack(tp: string) {
    if (live.tracked.has(tp)) live.tracked.delete(tp);
    else live.tracked.add(tp);
    tracked = new Set(live.tracked);
  }

  function onkey(e: KeyboardEvent) {
    const t = e.target as HTMLElement | null;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
    const action = actionForKey(e);
    if (!action) return;
    if (action === 'enter' && scene.kind === 'galaxy' && selectedSystem) {
      e.preventDefault();
      enterSystem(selectedSystem);
    } else if (action === 'exit') {
      e.preventDefault();
      // Progressive back-out: queue panel -> data panel -> exit the system.
      if (junctionQueueId) junctionQueueId = null;
      else if (panel) panel = null;
      else if (scene.kind === 'system') exitToGalaxy();
    } else if (action === 'zone') {
      e.preventDefault();
      zoneMode = !zoneMode;
      if (zoneMode) fitSignal++;
    } else if (action === 'fit') {
      e.preventDefault();
      fitSignal++;
    } else if (action === 'help') {
      e.preventDefault();
      showHelp = !showHelp;
    } else if (action === 'layers') {
      e.preventDefault();
      showLayers = !showLayers;
    } else if (action === 'playPause' && dev) {
      e.preventDefault();
      togglePlay();
    } else if (action === 'stepBack' && dev) {
      e.preventDefault();
      stepClock(-3600);
    } else if (action === 'stepForward' && dev) {
      e.preventDefault();
      stepClock(3600);
    }
  }

  onMount(() => {
    fetchGalaxy()
      .then((g) => (galaxy = g))
      .catch((e) => (error = e instanceof Error ? e.message : String(e)))
      .finally(() => (loading = false));
    live.onchange = () => {
      roster = [...live.roster];
      tracked = new Set(live.tracked);
      dev = live.dev;
      clockRate = live.rate;
    };
    live.start();
    window.addEventListener('keydown', onkey);
    return () => {
      window.removeEventListener('keydown', onkey);
      live.stop();
    };
  });
</script>

<main>
  {#if systemId === null}
    <GalaxyMap
      systems={galaxy.systems}
      links={galaxy.links}
      junctions={galaxy.junctions}
      selectedId={selectedSystem?.id ?? null}
      {fitSignal}
      {ships}
      {layers}
      onselect={(s) => {
        selectedSystem = s;
        selectedShip = null;
        panel = systemRows(s);
      }}
      onenter={enterSystem}
    />
  {:else}
    {#key systemId}
      <SystemMap
        {systemId}
        detail={systemDetail}
        junctions={galaxy.junctions}
        {zoneMode}
        {fitSignal}
        {ships}
        {layers}
        onselect={(d, body) => {
          junctionQueueId = null;
          panel = d;
          focusedBody = body;
        }}
        onexit={exitToGalaxy}
        onsummary={(s) => (summary = s)}
        onjunction={openQueue}
      />
    {/key}
  {/if}

  <div class="left-col">
    <AtAGlance
      breadcrumb={crumb}
      {placed}
      {stubbed}
      links={linkCount}
      inGalaxy={systemId === null}
      {summary}
      {loading}
      {error}
    />

    <FleetBoard
      {roster}
      {tracked}
      selected={selectedShip}
      {selectedRoute}
      onselect={selectShip}
      ontoggle={toggleTrack}
    />
  </div>

  <div class="overlay hints">
    {#if systemId === null}
      dbl-click / <kbd>Enter</kbd> a system · <kbd>f</kbd> fit
    {:else}
      <kbd>Esc</kbd> back · <kbd>z</kbd> zone{zoneMode ? ' ✓' : ''} · <kbd>f</kbd> fit
    {/if}
  </div>

  {#if junctionQueueId}
    {#key junctionQueueId}
      <JunctionQueuePanel
        junctionId={junctionQueueId}
        simNow={() => live.simNowMs()}
        onclose={() => (junctionQueueId = null)}
      />
    {/key}
  {:else if panel}
    <DataPanel detail={panel} onclose={() => (panel = null)} />
  {/if}

  {#if dev}
    <TimeScrubber
      simNow={() => live.simNowMs()}
      {clockRate}
      {scrubRate}
      ontogglePlay={togglePlay}
      onrate={setScrubRate}
      onstep={stepClock}
      onjumpnow={jumpNow}
    />
  {/if}

  <div class="right-col">
    {#if showLayers}
      <LayersPanel {layers} ontoggle={toggleLayer} />
    {/if}
    {#if systemId === null}
      <Legend />
    {/if}
  </div>

  {#if showHelp}
    <HelpOverlay onclose={() => (showHelp = false)} />
  {/if}
</main>

<style>
  /* Stack At-a-glance + the Fleet Board in one top-left column so they never
     overlap (their own top/left become inert once positioned statically here). */
  .left-col {
    position: absolute;
    top: 12px;
    left: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: calc(100vh - 24px);
  }
  .left-col :global(.overlay) {
    position: static;
  }
  /* Stack the Layers panel + Legend in a bottom-right column (no overlap). */
  .right-col {
    position: absolute;
    right: 12px;
    bottom: 12px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
    max-height: calc(100vh - 24px);
  }
  .right-col :global(.overlay) {
    position: static;
  }
  .hints {
    left: 12px;
    bottom: 12px;
    color: var(--muted);
    font-size: 11px;
  }
  kbd {
    background: #1d2940;
    border: 1px solid var(--panel-border);
    border-radius: 3px;
    padding: 0 4px;
  }
</style>
