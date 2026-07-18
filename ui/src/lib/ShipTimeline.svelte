<script lang="ts">
  import type { RouteOut, RouteSegment } from './api';
  import { legDurationS, legLabel, legProgress, splitLegs } from './timeline';

  let { route, percent = null }: { route: RouteOut; percent?: number | null } = $props();

  // Short glyph + colour per segment kind (see docs/terminology + the ASCII legend).
  const STYLE: Record<string, { glyph: string; color: string }> = {
    transit: { glyph: '-', color: '#3a4a6b' },
    hyper_cruise: { glyph: '*', color: '#5b4b8a' },
    wormhole_queue: { glyph: 'W', color: '#8a6d2f' },
    wormhole_transit: { glyph: 'V', color: '#b08a3a' },
    layover: { glyph: '=', color: '#3a5a44' }
  };

  const legs = $derived(splitLegs(route.segments));
  const prog = $derived(percent != null ? legProgress(legs, percent) : null);
  const clamp = (p: number) => Math.min(Math.max(p, 0), 1);

  // Segment view models sized ∝ duration within a given total (floor so instants show).
  function segViews(segments: RouteSegment[], total: number) {
    return segments.map((s) => ({
      pct: Math.max(s.duration_seconds / (total || 1), 0.02),
      style: STYLE[s.kind] ?? { glyph: '?', color: '#444' },
      title: `${s.kind} · ${s.duration_human}`
    }));
  }
</script>

{#if legs.length <= 1}
  <div class="timeline" title={route.total_duration_human}>
    {#each segViews(route.segments, route.total_duration_seconds || 1) as s, i (i)}
      <div class="seg" style="flex-grow:{s.pct}; background:{s.style.color}" title={s.title}>
        {s.style.glyph}
      </div>
    {/each}
    {#if percent != null}
      <div class="marker" style="left:{clamp(percent) * 100}%"></div>
    {/if}
  </div>
{:else}
  <!-- Multi-destination: one strip per leg, indented so the sequence reads down. -->
  <div class="legs">
    {#each legs as leg, i (i)}
      <div class="leg" style="margin-left:{i * 8}px">
        <div class="timeline" title={legLabel(leg)}>
          {#each segViews(leg, legDurationS(leg)) as s, j (j)}
            <div class="seg" style="flex-grow:{s.pct}; background:{s.style.color}" title={s.title}>
              {s.style.glyph}
            </div>
          {/each}
          {#if prog && prog.index === i}
            <div class="marker" style="left:{prog.local * 100}%"></div>
          {/if}
        </div>
        <span class="leg-label">→ {legLabel(leg)}</span>
      </div>
    {/each}
  </div>
{/if}

<style>
  .timeline {
    position: relative;
    display: flex;
    gap: 1px;
    height: 16px;
    margin: 4px 0 2px;
    border-radius: 3px;
    overflow: hidden;
    flex: 1;
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
  .legs {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .leg {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .leg-label {
    font-size: 10px;
    color: var(--muted);
    white-space: nowrap;
    max-width: 90px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
