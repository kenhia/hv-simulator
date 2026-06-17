<script lang="ts">
  let {
    breadcrumb,
    placed,
    stubbed,
    links,
    inGalaxy = true,
    loading = false,
    error = null
  }: {
    breadcrumb: string;
    placed: number;
    stubbed: number;
    links: number;
    inGalaxy?: boolean;
    loading?: boolean;
    error?: string | null;
  } = $props();
</script>

<div class="overlay glance">
  <div class="title">{breadcrumb}</div>
  {#if error}
    <div class="err">offline — {error}</div>
  {:else if loading}
    <div class="muted">loading…</div>
  {:else if inGalaxy}
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
  .title {
    color: var(--text);
    font-size: 14px;
    letter-spacing: 0.04em;
  }
  .err {
    color: #ff7a7a;
  }
</style>
