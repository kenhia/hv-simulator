<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchGalaxy,
    fetchSystemDetail,
    type Galaxy,
    type System,
    type SystemDetail
  } from '$lib/api';
  import { actionForKey } from '$lib/keymap';
  import { breadcrumb, GALAXY, type Scene } from '$lib/scene';
  import { systemRows, type Detail } from '$lib/detail';
  import AtAGlance from '$lib/AtAGlance.svelte';
  import DataPanel from '$lib/DataPanel.svelte';
  import GalaxyMap from '$lib/GalaxyMap.svelte';
  import Legend from '$lib/Legend.svelte';
  import SystemMap from '$lib/SystemMap.svelte';

  let galaxy = $state<Galaxy>({ systems: [], links: [], junctions: [] });
  let error = $state<string | null>(null);
  let loading = $state(true);

  let scene = $state<Scene>(GALAXY);
  let selectedSystem = $state<System | null>(null); // galaxy selection (Enter drills in)
  let systemDetail = $state<SystemDetail | null>(null);
  let panel = $state<Detail | null>(null);
  let focusedBody = $state<string | null>(null);
  let zoneMode = $state(false);
  let fitSignal = $state(0);
  let summary = $state<{ planets: number; moons: number; stations: number } | null>(null);

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
      if (scene.kind === 'system') exitToGalaxy();
      else panel = null;
    } else if (action === 'zone') {
      e.preventDefault();
      zoneMode = !zoneMode;
      if (zoneMode) fitSignal++; // entering zone mode recenters + frames the system
    } else if (action === 'fit') {
      e.preventDefault();
      fitSignal++;
    }
  }

  onMount(() => {
    fetchGalaxy()
      .then((g) => (galaxy = g))
      .catch((e) => (error = e instanceof Error ? e.message : String(e)))
      .finally(() => (loading = false));
    window.addEventListener('keydown', onkey);
    return () => window.removeEventListener('keydown', onkey);
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
      onselect={(s) => {
        selectedSystem = s;
        panel = systemRows(s);
      }}
      onenter={enterSystem}
    />
    <Legend />
  {:else}
    {#key systemId}
      <SystemMap
        {systemId}
        detail={systemDetail}
        {zoneMode}
        {fitSignal}
        onselect={(d, body) => {
          panel = d;
          focusedBody = body;
        }}
        onexit={exitToGalaxy}
        onsummary={(s) => (summary = s)}
      />
    {/key}
  {/if}

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

  <div class="overlay hints">
    {#if systemId === null}
      dbl-click / <kbd>Enter</kbd> a system · <kbd>f</kbd> fit
    {:else}
      <kbd>Esc</kbd> back · <kbd>z</kbd> zone{zoneMode ? ' ✓' : ''} · <kbd>f</kbd> fit
    {/if}
  </div>

  {#if panel}
    <DataPanel detail={panel} onclose={() => (panel = null)} />
  {/if}
</main>

<style>
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
