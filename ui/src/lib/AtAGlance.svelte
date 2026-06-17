<script lang="ts">
  interface Summary {
    planets: number;
    moons: number;
    stations: number;
  }

  let {
    breadcrumb,
    placed,
    stubbed,
    links,
    inGalaxy = true,
    summary = null,
    loading = false,
    error = null
  }: {
    breadcrumb: string;
    placed: number;
    stubbed: number;
    links: number;
    inGalaxy?: boolean;
    summary?: Summary | null;
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
  {:else if summary}
    <div>{summary.planets} planets</div>
    <div class="muted">{summary.moons} moons</div>
    <div>{summary.stations} stations</div>
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
