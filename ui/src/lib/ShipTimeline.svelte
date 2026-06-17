<script lang="ts">
  import type { RouteOut } from './api';

  let { route, percent = null }: { route: RouteOut; percent?: number | null } = $props();

  // Short glyph + colour per segment kind (see docs/terminology + the ASCII legend).
  const STYLE: Record<string, { glyph: string; color: string }> = {
    transit: { glyph: '-', color: '#3a4a6b' },
    hyper_cruise: { glyph: '*', color: '#5b4b8a' },
    wormhole_queue: { glyph: 'W', color: '#8a6d2f' },
    wormhole_transit: { glyph: 'V', color: '#b08a3a' },
    layover: { glyph: '=', color: '#3a5a44' }
  };

  const total = $derived(route.total_duration_seconds || 1);
  // Each segment gets a width ∝ its duration, with a floor so instant ones show.
  const segs = $derived(
    route.segments.map((s) => ({
      kind: s.kind,
      pct: Math.max(s.duration_seconds / total, 0.02),
      style: STYLE[s.kind] ?? { glyph: '?', color: '#444' },
      title: `${s.kind} · ${s.duration_human}`
    }))
  );
</script>

<div class="timeline" title={route.total_duration_human}>
  {#each segs as s, i (i)}
    <div class="seg" style="flex-grow:{s.pct}; background:{s.style.color}" title={s.title}>
      {s.style.glyph}
    </div>
  {/each}
  {#if percent != null}
    <div class="marker" style="left:{Math.min(Math.max(percent, 0), 1) * 100}%"></div>
  {/if}
</div>

<style>
  .timeline {
    position: relative;
    display: flex;
    gap: 1px;
    height: 16px;
    margin: 4px 0 2px;
    border-radius: 3px;
    overflow: hidden;
  }
  .seg {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    color: #cfd8e8;
    min-width: 6px;
  }
  .marker {
    position: absolute;
    top: -2px;
    bottom: -2px;
    width: 2px;
    background: #ff9d4d;
  }
</style>
