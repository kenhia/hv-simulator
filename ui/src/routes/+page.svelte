<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchGalaxy, type Galaxy, type System } from '$lib/api';
  import AtAGlance from '$lib/AtAGlance.svelte';
  import DataPanel from '$lib/DataPanel.svelte';
  import GalaxyMap from '$lib/GalaxyMap.svelte';
  import Legend from '$lib/Legend.svelte';

  let galaxy = $state<Galaxy>({ systems: [], links: [], junctions: [] });
  let selected = $state<System | null>(null);
  let error = $state<string | null>(null);
  let loading = $state(true);

  const placed = $derived(galaxy.systems.filter((s) => s.coordinates !== null).length);
  const stubbed = $derived(galaxy.systems.length - placed);
  const links = $derived(
    galaxy.links.filter((l) => l.transit === 'instant' && l.to_system_id !== null).length
  );

  onMount(async () => {
    try {
      galaxy = await fetchGalaxy();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });
</script>

<main>
  <GalaxyMap
    systems={galaxy.systems}
    links={galaxy.links}
    junctions={galaxy.junctions}
    selectedId={selected?.id ?? null}
    onselect={(s) => (selected = s)}
  />
  <AtAGlance {placed} {stubbed} {links} {loading} {error} />
  <Legend />
  {#if selected}
    <DataPanel system={selected} junctions={galaxy.junctions} onclose={() => (selected = null)} />
  {/if}
</main>
