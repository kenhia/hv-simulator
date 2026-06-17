<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchJunctionQueue, type JunctionQueue } from './api';
  import { etaText } from './format';

  let {
    junctionId,
    simNow,
    onclose
  }: { junctionId: string; simNow: () => number; onclose?: () => void } = $props();

  let queue = $state<JunctionQueue | null>(null);
  let nowMs = $state(0);
  let error = $state(false);

  async function poll() {
    try {
      queue = await fetchJunctionQueue(junctionId, new Date(simNow()).toISOString());
      error = false;
    } catch {
      error = true;
    }
  }

  onMount(() => {
    nowMs = simNow();
    poll();
    const p = setInterval(poll, 4000); // refresh the entry set
    const t = setInterval(() => (nowMs = simNow()), 1000); // smooth the countdown
    return () => {
      clearInterval(p);
      clearInterval(t);
    };
  });
</script>

<aside class="overlay panel">
  <button class="close" onclick={() => onclose?.()} aria-label="close">×</button>
  <div class="title">JUNCTION QUEUE</div>
  <h2>{queue?.junction_id ?? junctionId}</h2>
  {#if queue}
    <div class="muted">traffic intensity {queue.traffic_intensity ?? '—'}</div>
    {#if queue.entries.length === 0}
      <div class="muted empty">no transits queued</div>
    {:else}
      <ol class="rows">
        {#each queue.entries as e (e.position)}
          <li class:phantom={e.transponder === null}>
            <span class="pos">#{e.position}</span>
            <span class="who">{e.transponder ?? '(phantom)'}</span>
            <span class="eta muted">{etaText(Date.parse(e.transit_eta), nowMs)}</span>
          </li>
        {/each}
      </ol>
    {/if}
  {:else if error}
    <div class="err">queue unavailable</div>
  {:else}
    <div class="muted">loading…</div>
  {/if}
</aside>

<style>
  .panel {
    top: 12px;
    right: 12px;
    width: 280px;
    max-height: 70vh;
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
  h2 {
    margin: 2px 0 6px;
    font-size: 15px;
    word-break: break-word;
  }
  .rows {
    list-style: none;
    margin: 6px 0 0;
    padding: 0;
    overflow-y: auto;
  }
  .rows li {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 8px;
    align-items: baseline;
    padding: 1px 0;
  }
  .pos {
    color: #ff9d4d;
  }
  .who {
    color: #ffb3b3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .phantom .who {
    color: var(--muted);
  }
  .empty {
    padding: 6px 0;
  }
  .err {
    color: #ff7a7a;
  }
</style>
