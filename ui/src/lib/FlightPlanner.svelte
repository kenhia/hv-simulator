<script lang="ts">
  import {
    fetchSystemBodies,
    postFleetRoute,
    postPlan,
    type PlanResult,
    type ShipCatalogEntry,
    type System,
    type SystemBody
  } from './api';
  import { canPlan, defaultLayoverS, routeSystems, toPlanRequest, type Waypoint } from './planner';
  import ShipTimeline from './ShipTimeline.svelte';

  let {
    catalog = [],
    systems = [],
    onclose,
    onfiled,
    onpreview
  }: {
    catalog?: ShipCatalogEntry[];
    systems?: System[];
    onclose?: () => void;
    onfiled?: (tp: string) => void;
    onpreview?: (path: string[] | null) => void;
  } = $props();

  const placed = $derived(
    systems.filter((s) => s.coordinates !== null).sort((a, b) => a.name.localeCompare(b.name))
  );

  let tp = $state('');
  let origin = $state<{ system: string; body: string }>({ system: '', body: '' });
  let waypoints = $state<Waypoint[]>([]);
  let bodies = $state<Record<string, SystemBody[]>>({});
  let plan = $state<PlanResult | null>(null);
  let error = $state('');
  let busy = $state(false);

  const ship = $derived(catalog.find((c) => c.transponder === tp) ?? null);
  const ready = $derived(canPlan(tp, origin, waypoints));

  async function loadBodies(sys: string) {
    if (!sys || bodies[sys]) return;
    try {
      bodies = { ...bodies, [sys]: await fetchSystemBodies(sys) };
    } catch {
      bodies = { ...bodies, [sys]: [] };
    }
  }

  function invalidate() {
    plan = null;
    onpreview?.(null);
  }

  // Pick a ship; prefill the origin from its current navigable point (an arrived /
  // idle ship sits somewhere fileable). Ships never filed have no known location.
  function setShip(newTp: string) {
    tp = newTp;
    const c = catalog.find((e) => e.transponder === newTp);
    if (c?.location_system && c.location_body) {
      origin = { system: c.location_system, body: c.location_body };
      loadBodies(c.location_system);
    } else {
      origin = { system: '', body: '' };
    }
    waypoints = [];
    invalidate();
  }

  function setOriginSystem(sys: string) {
    origin = { system: sys, body: '' };
    loadBodies(sys);
    invalidate();
  }
  function setOriginBody(body: string) {
    origin = { ...origin, body };
    invalidate();
  }
  function addWaypoint() {
    waypoints = [
      ...waypoints,
      { system: '', body: '', layover_s: defaultLayoverS(ship?.military ?? false) }
    ];
    invalidate();
  }
  function setWpSystem(i: number, sys: string) {
    waypoints = waypoints.map((w, j) => (j === i ? { ...w, system: sys, body: '' } : w));
    loadBodies(sys);
    invalidate();
  }
  function setWpBody(i: number, body: string) {
    waypoints = waypoints.map((w, j) => (j === i ? { ...w, body } : w));
    invalidate();
  }
  function setWpLayoverH(i: number, hours: number) {
    waypoints = waypoints.map((w, j) =>
      j === i ? { ...w, layover_s: Math.max(0, hours) * 3600 } : w
    );
    invalidate();
  }
  function removeWaypoint(i: number) {
    waypoints = waypoints.filter((_, j) => j !== i);
    invalidate();
  }

  async function doPlan() {
    error = '';
    busy = true;
    try {
      plan = await postPlan(toPlanRequest(tp, origin, waypoints));
      onpreview?.(routeSystems(plan.filed));
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      plan = null;
    } finally {
      busy = false;
    }
  }

  async function doSubmit() {
    if (!plan) return;
    error = '';
    busy = true;
    try {
      await postFleetRoute(plan.filed);
      onpreview?.(null);
      onfiled?.(tp);
      onclose?.();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e); // e.g. 409 at-origin guard
    } finally {
      busy = false;
    }
  }
</script>

<aside class="overlay planner">
  <button class="close" onclick={() => onclose?.()} aria-label="close">×</button>
  <div class="title">FLIGHT PLANNER</div>

  <label
    >ship
    <select value={tp} onchange={(e) => setShip(e.currentTarget.value)}>
      <option value="" disabled>— pick a ship —</option>
      {#each catalog as c (c.transponder)}
        <option value={c.transponder}>
          {c.name} · {c.transponder}{c.under_way ? ' (under way)' : ''}
        </option>
      {/each}
    </select>
  </label>
  {#if ship?.under_way}
    <div class="warn">under way — re-routing is deferred; submit may be rejected</div>
  {/if}

  <div class="seg-label">origin</div>
  <div class="loc">
    <select value={origin.system} onchange={(e) => setOriginSystem(e.currentTarget.value)}>
      <option value="" disabled>system</option>
      {#each placed as s (s.id)}<option value={s.id}>{s.name}</option>{/each}
    </select>
    <select value={origin.body} onchange={(e) => setOriginBody(e.currentTarget.value)}>
      <option value="" disabled>body</option>
      {#each bodies[origin.system] ?? [] as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
    </select>
  </div>

  <div class="seg-label">destinations</div>
  {#each waypoints as w, i (i)}
    <div class="loc wp">
      <select value={w.system} onchange={(e) => setWpSystem(i, e.currentTarget.value)}>
        <option value="" disabled>system</option>
        {#each placed as s (s.id)}<option value={s.id}>{s.name}</option>{/each}
      </select>
      <select value={w.body} onchange={(e) => setWpBody(i, e.currentTarget.value)}>
        <option value="" disabled>body</option>
        {#each bodies[w.system] ?? [] as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
      </select>
      <input
        class="lay"
        type="number"
        min="0"
        step="0.5"
        value={w.layover_s / 3600}
        title="layover (hours)"
        onchange={(e) => setWpLayoverH(i, Number(e.currentTarget.value))}
      />h
      <button class="rm" onclick={() => removeWaypoint(i)} aria-label="remove">×</button>
    </div>
  {/each}
  <button class="add" onclick={addWaypoint} disabled={!tp}>+ destination</button>

  <div class="actions">
    <button onclick={doPlan} disabled={!ready || busy}>Plan</button>
    <button class="primary" onclick={doSubmit} disabled={!plan || busy}>Submit</button>
  </div>

  {#if error}<div class="err">{error}</div>{/if}
  {#if plan}
    <div class="preview">
      <div>ETA {plan.route.total_duration_human} · {plan.route.segments.length} segments</div>
      <ShipTimeline route={plan.route} />
      <div class="muted">arrive {plan.route.arrival.slice(0, 16).replace('T', ' ')}</div>
    </div>
  {/if}
</aside>

<style>
  .planner {
    top: 12px;
    right: 12px;
    width: 300px;
    max-height: calc(100vh - 24px);
    overflow-y: auto;
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
  }
  label {
    display: block;
    margin: 6px 0;
  }
  .seg-label {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 0.08em;
    margin: 8px 0 2px;
  }
  select,
  input {
    background: #0c1322;
    border: 1px solid var(--panel-border);
    color: var(--text);
    border-radius: 4px;
    padding: 2px 4px;
    font: inherit;
  }
  .loc {
    display: flex;
    gap: 4px;
    align-items: center;
    margin: 2px 0;
  }
  .loc select {
    flex: 1;
    min-width: 0;
  }
  .lay {
    width: 48px;
  }
  .rm,
  .add {
    background: #1d2940;
    border: 1px solid var(--panel-border);
    color: var(--text);
    border-radius: 4px;
    cursor: pointer;
    font: inherit;
  }
  .add {
    margin-top: 4px;
    padding: 2px 8px;
  }
  .actions {
    display: flex;
    gap: 6px;
    margin: 10px 0 4px;
  }
  .actions button {
    flex: 1;
    background: #1d2940;
    border: 1px solid var(--panel-border);
    color: var(--text);
    border-radius: 4px;
    padding: 3px;
    cursor: pointer;
    font: inherit;
  }
  .actions button.primary {
    border-color: var(--accent);
    color: var(--accent);
  }
  .actions button:disabled {
    opacity: 0.4;
    cursor: default;
  }
  .warn {
    color: #caa64a;
    font-size: 11px;
  }
  .err {
    color: #ff7a7a;
    font-size: 11px;
    margin-top: 4px;
  }
  .preview {
    margin-top: 8px;
    border-top: 1px solid var(--panel-border);
    padding-top: 6px;
  }
</style>
