<script lang="ts">
  import { KEYMAP } from './keymap';
  let { onclose }: { onclose?: () => void } = $props();
  const active = KEYMAP.filter((b) => b.active);
  function label(key: string): string {
    return key === ' ' ? 'Space' : key;
  }
</script>

<div
  class="scrim"
  role="button"
  tabindex="0"
  onclick={() => onclose?.()}
  onkeydown={(e) => e.key === 'Escape' && onclose?.()}
>
  <div class="overlay card" role="dialog" aria-label="keyboard shortcuts">
    <div class="title">SHORTCUTS</div>
    <dl>
      {#each active as b (b.key)}
        <dt><kbd>{label(b.key)}</kbd></dt>
        <dd>{b.label}</dd>
      {/each}
    </dl>
    <div class="muted hint">
      mouse: drag pan · wheel zoom · dbl-click a system · click to select
    </div>
  </div>
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgba(6, 10, 18, 0.55);
  }
  .card {
    min-width: 280px;
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 12px;
    margin: 6px 0;
  }
  dt {
    text-align: right;
  }
  dd {
    margin: 0;
  }
  kbd {
    background: #1d2940;
    border: 1px solid var(--panel-border);
    border-radius: 3px;
    padding: 0 5px;
  }
  .hint {
    margin-top: 8px;
    font-size: 11px;
  }
</style>
