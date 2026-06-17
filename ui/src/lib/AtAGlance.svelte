<script lang="ts">
  let {
    placed,
    stubbed,
    links,
    loading = false,
    error = null
  }: {
    placed: number;
    stubbed: number;
    links: number;
    loading?: boolean;
    error?: string | null;
  } = $props();
</script>

<div class="overlay glance">
  <div class="title">GALAXY</div>
  {#if error}
    <div class="err">offline — {error}</div>
  {:else if loading}
    <div class="muted">loading…</div>
  {:else}
    <div>{placed} systems placed</div>
    <div class="muted">{stubbed} stubbed (no coords)</div>
    <div>{links} wormhole links</div>
  {/if}
</div>

<style>
  .glance {
    top: 12px;
    left: 12px;
    min-width: 160px;
  }
  .err {
    color: #ff7a7a;
  }
</style>
