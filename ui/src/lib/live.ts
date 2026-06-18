// The live fleet: polls the engine for the sim clock, the roster, and per-ship
// state, and dead-reckons positions between polls so the maps animate smoothly.
// The pure helpers (simNowMs, deadReckon, unit conversions) are unit-tested; the
// controller does the I/O.

import { fetchClock, fetchFleet, fetchShipState, type FleetEntry, type Vec3 } from './api';

// 1 ly = 9.4607e15 m = 9.4607e12 km; 1 AU = 1.495978707e11 m = 1.495978707e8 km.
const KM_PER_LY = 9.4607304725808e12;
const KM_PER_AU = 1.495978707e8;

export interface SimClockModel {
  simEpochMs: number;
  realEpochMs: number;
  rate: number;
}

// Local sim-time: extrapolate from the clock model + the real wall clock.
export function simNowMs(c: SimClockModel, wallMs: number): number {
  return c.simEpochMs + (wallMs - c.realEpochMs) * c.rate;
}

// Linear extrapolation of a position (km) by its velocity (km/s) to `nowMs`.
export function deadReckon(posKm: Vec3, velKmS: Vec3, whenMs: number, nowMs: number): Vec3 {
  const dt = (nowMs - whenMs) / 1000;
  return {
    x: posKm.x + velKmS.x * dt,
    y: posKm.y + velKmS.y * dt,
    z: posKm.z + velKmS.z * dt
  };
}

export const kmToLy = (km: number): number => km / KM_PER_LY;
export const kmToAu = (km: number): number => km / KM_PER_AU;

export interface LiveShip {
  transponder: string;
  ship: string;
  phase: string;
  frame: 'heliocentric' | 'galactic';
  system: string | null;
  posKm: Vec3; // dead-reckoned to the query time
  velKmS: Vec3;
  eta: string | null;
  queuePosition: number | null;
}

interface ShipSample {
  posKm: Vec3;
  velKmS: Vec3;
  whenMs: number;
  frame: 'heliocentric' | 'galactic';
  system: string | null;
  phase: string;
  eta: string | null;
  queuePosition: number | null;
}

export class LiveFleet {
  clock: SimClockModel | null = null;
  rate = 1; // current sim-clock rate (0 = paused)
  dev = false; // /clock dev_controls_enabled — gates the time scrubber
  roster: FleetEntry[] = [];
  tracked = new Set<string>();
  onchange: (() => void) | null = null;

  private samples = new Map<string, ShipSample>();
  private timers: ReturnType<typeof setInterval>[] = [];

  start(): void {
    void this.pollClock();
    void this.pollFleet();
    this.timers.push(setInterval(() => void this.pollClock(), 30_000));
    this.timers.push(setInterval(() => void this.pollFleet(), 5_000));
    this.timers.push(setInterval(() => void this.pollStates(), 5_000));
  }

  stop(): void {
    for (const t of this.timers) clearInterval(t);
    this.timers = [];
  }

  simNowMs(): number {
    const wall = Date.now();
    return this.clock ? simNowMs(this.clock, wall) : wall;
  }

  // Dead-reckoned snapshot of every tracked ship that has a sample.
  ships(): LiveShip[] {
    const now = this.simNowMs();
    const byTp = new Map(this.roster.map((e) => [e.transponder, e]));
    const out: LiveShip[] = [];
    for (const tp of this.tracked) {
      const s = this.samples.get(tp);
      if (!s) continue;
      out.push({
        transponder: tp,
        ship: byTp.get(tp)?.ship ?? tp,
        phase: s.phase,
        frame: s.frame,
        system: s.system,
        posKm: deadReckon(s.posKm, s.velKmS, s.whenMs, now),
        velKmS: s.velKmS,
        eta: s.eta,
        queuePosition: s.queuePosition
      });
    }
    return out;
  }

  // Re-fetch the clock (call after a scrubber PUT so the view tracks it at once).
  async resyncClock(): Promise<void> {
    await this.pollClock();
  }

  // Re-fetch the roster now (call after filing a route so it appears at once).
  async refreshFleet(): Promise<void> {
    await this.pollFleet();
  }

  private async pollClock(): Promise<void> {
    try {
      const c = await fetchClock();
      this.clock = {
        simEpochMs: Date.parse(c.sim_epoch),
        realEpochMs: Date.parse(c.real_epoch),
        rate: c.rate
      };
      this.rate = c.rate;
      this.dev = c.dev_controls_enabled;
      this.onchange?.();
    } catch {
      /* keep the last clock; the local wall clock still advances */
    }
  }

  private async pollFleet(): Promise<void> {
    try {
      const f = await fetchFleet();
      this.roster = f.ships;
      // Default: track the whole (small) active fleet until the user narrows it.
      if (this.tracked.size === 0) for (const e of f.ships) this.tracked.add(e.transponder);
      this.onchange?.();
    } catch {
      /* transient; keep the last roster */
    }
  }

  private async pollStates(): Promise<void> {
    await Promise.all(
      [...this.tracked].map(async (tp) => {
        try {
          const st = await fetchShipState(tp);
          this.samples.set(tp, {
            posKm: st.position.km,
            velKmS: st.velocity.km_s,
            whenMs: Date.parse(st.when),
            frame: st.frame,
            system: st.system,
            phase: st.phase,
            eta: st.eta,
            queuePosition: st.queue_position
          });
        } catch {
          /* drop this tick for this ship */
        }
      })
    );
  }
}
