<script lang="ts">
  import { onMount } from 'svelte';

  let {
    simNow,
    clockRate,
    scrubRate,
    ontogglePlay,
    onrate,
    onstep,
    onjumpnow
  }: {
    simNow: () => number;
    clockRate: number;
    scrubRate: number;
    ontogglePlay?: () => void;
    onrate?: (r: number) => void;
    onstep?: (seconds: number) => void;
    onjumpnow?: () => void;
  } = $props();

  const RATES = [1, 60, 3600, 86400];
  const STEP = 3600; // 1 sim-hour per step
  let label = $state('');
  const playing = $derived(clockRate > 0);

  function fmt(ms: number): string {
    return new Date(ms).toISOString().replace('T', ' ').slice(0, 19);
  }

  onMount(() => {
    label = fmt(simNow());
    const t = setInterval(() => (label = fmt(simNow())), 250);
    return () => clearInterval(t);
  });
</script>

<div class="overlay scrubber">
  <button class="play" onclick={() => ontogglePlay?.()} title="play / pause (Space)">
    {playing ? '⏸' : '▶'}
  </button>
  <button onclick={() => onstep?.(-STEP)} title="step back 1h (,)">«</button>
  <button onclick={() => onstep?.(STEP)} title="step forward 1h (.)">»</button>
  <span class="time">{label}</span>
  <span class="muted rate">{playing ? `×${clockRate}` : 'paused'}</span>
  <span class="rates">
    {#each RATES as r (r)}
      <button class:sel={r === scrubRate} onclick={() => onrate?.(r)}>×{r}</button>
    {/each}
  </span>
  <button onclick={() => onjumpnow?.()} title="jump to real now">now</button>
</div>

<style>
  .scrubber {
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .scrubber button {
    background: #1d2940;
    border: 1px solid var(--panel-border);
    color: var(--text);
    border-radius: 4px;
    padding: 1px 6px;
    cursor: pointer;
    font: inherit;
  }
  .scrubber button.sel {
    border-color: var(--accent);
    color: var(--accent);
  }
  .time {
    font-variant-numeric: tabular-nums;
  }
  .rate {
    min-width: 56px;
  }
  .rates {
    display: flex;
    gap: 3px;
  }
</style>
