<script lang="ts">
  import type { FleetEntry, RouteOut } from './api';
  import { phaseStyle } from './phase';
  import ShipTimeline from './ShipTimeline.svelte';

  let {
    roster = [],
    tracked,
    selected = null,
    selectedRoute = null,
    onselect,
    ontoggle
  }: {
    roster?: FleetEntry[];
    tracked: Set<string>;
    selected?: string | null;
    selectedRoute?: RouteOut | null;
    onselect?: (tp: string) => void;
    ontoggle?: (tp: string) => void;
  } = $props();

  let collapsed = $state(false);
  let query = $state('');

  const shown = $derived(
    roster.filter((e) => {
      const q = query.trim().toLowerCase();
      return !q || e.transponder.toLowerCase().includes(q) || e.ship.toLowerCase().includes(q);
    })
  );
</script>

<div class="overlay board">
  <div class="head">
    <button class="toggle" onclick={() => (collapsed = !collapsed)} title="toggle fleet board">
      {collapsed ? '▸' : '▾'}
    </button>
    <span class="title">FLEET</span>
    <span class="muted">{roster.length}</span>
  </div>
  {#if !collapsed}
    <input class="search" placeholder="find ship…" bind:value={query} />
    <div class="rows">
      {#each shown as e (e.transponder)}
        <div class="row" class:sel={e.transponder === selected}>
          <input
            type="checkbox"
            checked={tracked.has(e.transponder)}
            onchange={() => ontoggle?.(e.transponder)}
            title="show on map"
          />
          <button class="entry" onclick={() => onselect?.(e.transponder)}>
            <span class="tp">{e.transponder}</span>
            <span
              class="gl"
              style="color:{phaseStyle(e.phase).color}"
              title="{phaseStyle(e.phase).label}{e.queue_position != null
                ? ` · #${e.queue_position}`
                : ''}">{phaseStyle(e.phase).glyph}</span
            >
            <span class="nm">{e.ship}</span>
          </button>
        </div>
        {#if e.transponder === selected && selectedRoute}
          <ShipTimeline route={selectedRoute} percent={e.percent_complete} />
          <div class="itin muted">
            {selectedRoute.origin.body} → {selectedRoute.segments.at(-1)?.body ?? '—'}
          </div>
        {/if}
      {/each}
      {#if shown.length === 0}
        <div class="muted empty">no ships</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .board {
    top: 96px;
    left: 12px;
    width: 250px;
    max-height: 50vh;
    display: flex;
    flex-direction: column;
  }
  .head {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .toggle {
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 0;
  }
  .title {
    letter-spacing: 0.12em;
    font-size: 11px;
    color: var(--muted);
  }
  .search {
    margin: 6px 0;
    width: 100%;
    background: #0c1322;
    border: 1px solid var(--panel-border);
    color: var(--text);
    border-radius: 4px;
    padding: 3px 6px;
    font: inherit;
  }
  .rows {
    overflow-y: auto;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .row.sel {
    background: #1d2940;
    border-radius: 4px;
  }
  .entry {
    flex: 1;
    display: grid;
    grid-template-columns: auto auto 1fr;
    gap: 6px;
    align-items: baseline;
    background: none;
    border: none;
    color: var(--text);
    text-align: left;
    cursor: pointer;
    padding: 2px 2px;
    font: inherit;
  }
  .tp {
    color: #ffb3b3;
  }
  .gl {
    width: 1ch;
    text-align: center;
  }
  .nm {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .empty {
    padding: 4px;
  }
</style>
