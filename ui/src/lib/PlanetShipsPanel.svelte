<script lang="ts">
  import type { FleetEntry } from './api';
  import { phaseStyle } from './phase';

  let {
    name,
    transponders = [],
    roster = [],
    onselect,
    onclose
  }: {
    name: string;
    transponders?: string[];
    roster?: FleetEntry[];
    onselect?: (tp: string) => void;
    onclose?: () => void;
  } = $props();

  let query = $state('');
  const byTp = $derived(new Map(roster.map((e) => [e.transponder, e])));
  // The ships parked here, resolved to their roster entry (for name + phase glyph).
  const rows = $derived(
    transponders
      .map((tp) => byTp.get(tp))
      .filter((e): e is FleetEntry => e != null)
      .filter((e) => {
        const q = query.trim().toLowerCase();
        return !q || e.transponder.toLowerCase().includes(q) || e.ship.toLowerCase().includes(q);
      })
  );
</script>

<aside class="overlay panel">
  <button class="close" onclick={() => onclose?.()} aria-label="close">×</button>
  <div class="title">AT REST</div>
  <h2>{name}</h2>
  <div class="muted">{transponders.length} ship{transponders.length === 1 ? '' : 's'} at rest</div>
  <input class="search" placeholder="find ship…" bind:value={query} />
  <div class="rows">
    {#each rows as e (e.transponder)}
      <button class="row" onclick={() => onselect?.(e.transponder)}>
        <span class="tp">{e.transponder}</span>
        <span class="gl" style="color:{phaseStyle(e.phase).color}" title={phaseStyle(e.phase).label}
          >{phaseStyle(e.phase).glyph}</span
        >
        <span class="nm">{e.ship}</span>
      </button>
    {/each}
    {#if rows.length === 0}<div class="muted empty">none</div>{/if}
  </div>
</aside>

<style>
  .panel {
    top: 12px;
    right: 12px;
    width: 260px;
    max-height: calc(100vh - 24px);
    display: flex;
    flex-direction: column;
  }
  .close {
    position: absolute;
    top: 6px;
    right: 8px;
    background: none;
    border: none;
    color: var(--muted);
    font-size: 18px;
    cursor: pointer;
    line-height: 1;
  }
  .title {
    letter-spacing: 0.12em;
    font-size: 11px;
    color: var(--muted);
  }
  h2 {
    margin: 2px 0 4px;
    font-size: 16px;
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
    display: grid;
    grid-template-columns: auto auto 1fr;
    gap: 6px;
    width: 100%;
    align-items: baseline;
    background: none;
    border: none;
    color: var(--text);
    text-align: left;
    cursor: pointer;
    padding: 2px;
    font: inherit;
  }
  .row:hover {
    background: #1d2940;
    border-radius: 4px;
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
