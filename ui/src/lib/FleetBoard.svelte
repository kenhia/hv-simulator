<script lang="ts">
  import type { FleetEntry, RouteOut } from './api';
  import { boardFilter, isFilterActive, nationsPresent } from './board';
  import { nationName } from './nation';
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
  let showFilter = $state(false);
  let hideArrived = $state(false);
  let nationHidden = $state(new Set<string>()); // nations unchecked (hidden); all shown by default

  const nations = $derived(nationsPresent(roster));
  // boardFilter takes a *show* set (empty = all); derive it from the hidden set.
  const showNations = $derived(
    nationHidden.size === 0
      ? new Set<string>()
      : new Set(nations.filter((n) => !nationHidden.has(n)))
  );
  const filter = $derived({ hideArrived, nations: showNations });
  const active = $derived(isFilterActive(filter));

  const shown = $derived(
    boardFilter(roster, filter).filter((e) => {
      const q = query.trim().toLowerCase();
      return !q || e.transponder.toLowerCase().includes(q) || e.ship.toLowerCase().includes(q);
    })
  );

  function toggleNation(code: string) {
    const next = new Set(nationHidden);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    nationHidden = next;
  }
</script>

<div class="overlay board">
  <div class="head">
    <button class="toggle" onclick={() => (collapsed = !collapsed)} title="toggle fleet board">
      {collapsed ? '▸' : '▾'}
    </button>
    <span class="title">FLEET</span>
    <span class="muted">{active ? `${shown.length}/${roster.length}` : roster.length}</span>
    {#if !collapsed}
      <button
        class="filt"
        class:on={active}
        onclick={() => (showFilter = !showFilter)}
        title="filter the board">⛃{active ? ' •' : ''}</button
      >
    {/if}
  </div>
  {#if !collapsed}
    {#if showFilter}
      <div class="filter">
        <label class="frow">
          <input type="checkbox" bind:checked={hideArrived} /> hide arrived
        </label>
        {#if nations.length > 1}
          <div class="seg">nations</div>
          {#each nations as code (code)}
            <label class="frow">
              <input
                type="checkbox"
                checked={!nationHidden.has(code)}
                onchange={() => toggleNation(code)}
              />
              {nationName(code)}
            </label>
          {/each}
        {/if}
      </div>
    {/if}
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
  .filt {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 0;
    font: inherit;
  }
  .filt.on {
    color: var(--accent);
  }
  .filter {
    margin: 6px 0;
    padding: 6px;
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    background: #0c1322;
  }
  .frow {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    padding: 1px 0;
  }
  .seg {
    color: var(--muted);
    font-size: 10px;
    letter-spacing: 0.08em;
    margin: 4px 0 2px;
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
