<script lang="ts">
  import type { Junction, System } from './api';

  let {
    system,
    junctions = [],
    onclose
  }: {
    system: System;
    junctions?: Junction[];
    onclose?: () => void;
  } = $props();

  const host = $derived(junctions.find((j) => j.host_system_id === system.id) ?? null);

  function coords(s: System): string {
    const c = s.coordinates;
    return c ? `${c.x_ly.toFixed(1)}, ${c.y_ly.toFixed(1)}, ${c.z_ly.toFixed(1)} ly` : '—';
  }
</script>

<aside class="overlay panel">
  <button class="close" onclick={() => onclose?.()} aria-label="close">×</button>
  <div class="title">SYSTEM</div>
  <h2>{system.name}</h2>
  <dl>
    <dt>id</dt>
    <dd>{system.id}</dd>
    <dt>nation</dt>
    <dd>{system.star_nation_id ?? '—'}</dd>
    <dt>type</dt>
    <dd>{system.is_binary ? 'binary' : 'single star'}</dd>
    <dt>distance</dt>
    <dd>{system.distance_ly != null ? `${system.distance_ly.toFixed(1)} ly` : '—'}</dd>
    <dt>galactic</dt>
    <dd>{coords(system)}</dd>
    {#if host}
      <dt>junction</dt>
      <dd>
        {host.name}{host.traffic_intensity != null ? ` (knob ${host.traffic_intensity})` : ''}
      </dd>
    {/if}
  </dl>
</aside>

<style>
  .panel {
    top: 12px;
    right: 12px;
    width: 280px;
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
  h2 {
    margin: 2px 0 10px;
    font-size: 16px;
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2px 12px;
    margin: 0;
  }
  dt {
    color: var(--muted);
  }
  dd {
    margin: 0;
    word-break: break-word;
  }
</style>
