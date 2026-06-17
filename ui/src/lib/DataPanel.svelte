<script lang="ts">
  import type { Detail } from './detail';

  let { detail, onclose }: { detail: Detail; onclose?: () => void } = $props();
</script>

<aside class="overlay panel">
  <button class="close" onclick={() => onclose?.()} aria-label="close">×</button>
  <div class="title">{detail.kind.toUpperCase()}</div>
  <h2>{detail.title}</h2>
  <dl>
    {#each detail.rows as [k, v] (k)}
      <dt>{k}</dt>
      <dd>{v}</dd>
    {/each}
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
