<script lang="ts">
  import { LAYER_ROWS, type Layers } from './layers';
  let { layers, ontoggle }: { layers: Layers; ontoggle?: (key: keyof Layers) => void } = $props();
</script>

<div class="overlay layers">
  <div class="title">LAYERS</div>
  {#each LAYER_ROWS as [key, label] (key)}
    <label class="row">
      <input type="checkbox" checked={layers[key]} onchange={() => ontoggle?.(key)} />
      {label}
    </label>
  {/each}
</div>

<style>
  .row {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
</style>
