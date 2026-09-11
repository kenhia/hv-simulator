import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchClock, fetchFleet, fetchShipState } from './api';
import { LiveFleet, deadReckon, kmToAu, kmToLy, simNowMs, type SimClockModel } from './live';

// The controller does I/O; these tests are about *when* it does it, so the
// engine calls are stubbed rather than served.
vi.mock('./api', () => ({
  fetchClock: vi.fn(),
  fetchFleet: vi.fn(),
  fetchShipState: vi.fn()
}));

beforeEach(() => {
  vi.mocked(fetchClock).mockResolvedValue({
    sim_epoch: '1890-01-01T00:00:00+00:00',
    real_epoch: '1890-01-01T00:00:00+00:00',
    rate: 1,
    dev_controls_enabled: false
  } as never);
  vi.mocked(fetchFleet).mockResolvedValue({ ships: [] } as never);
  vi.mocked(fetchShipState).mockRejectedValue(new Error('not under test'));
});

describe('simNowMs', () => {
  it('advances at the clock rate from the epochs', () => {
    const c: SimClockModel = { simEpochMs: 1000, realEpochMs: 0, rate: 1 };
    expect(simNowMs(c, 5000)).toBe(6000); // sim_epoch + (wall - real_epoch)*rate
  });
  it('honours an accelerated rate', () => {
    const c: SimClockModel = { simEpochMs: 0, realEpochMs: 0, rate: 60 };
    expect(simNowMs(c, 1000)).toBe(60_000); // 1 real s -> 60 sim s
  });
});

describe('deadReckon', () => {
  it('extrapolates linearly by velocity over elapsed seconds', () => {
    const p = deadReckon(
      { x: 0, y: 0, z: 0 },
      { x: 10, y: -2, z: 0 }, // km/s
      1000,
      3000 // 2 s later
    );
    expect(p).toEqual({ x: 20, y: -4, z: 0 });
  });
});

describe('unit conversions', () => {
  it('km -> ly and km -> AU are in the right ballpark', () => {
    expect(kmToLy(9.4607304725808e12)).toBeCloseTo(1, 9);
    expect(kmToAu(1.495978707e8)).toBeCloseTo(1, 9);
  });
});

// --- Sprint 040: the poll pauses while the tab is hidden (#477) ---------------

describe('LiveFleet polling', () => {
  it('goes silent while hidden and catches up on return', async () => {
    vi.useFakeTimers();
    const live = new LiveFleet();
    live.start();
    expect(live.polling).toBe(true);

    const afterStart = vi.mocked(fetchFleet).mock.calls.length;
    await vi.advanceTimersByTimeAsync(15_000);
    expect(vi.mocked(fetchFleet).mock.calls.length).toBeGreaterThan(afterStart);

    // Hidden: the timers are torn down, so a forgotten tab costs the engine
    // nothing at all rather than a request every 5 s forever.
    live.setHidden(true);
    expect(live.polling).toBe(false);
    const whileHidden = vi.mocked(fetchFleet).mock.calls.length;
    await vi.advanceTimersByTimeAsync(120_000);
    expect(vi.mocked(fetchFleet).mock.calls.length).toBe(whileHidden);

    // Visible again: poll now, not one interval from now.
    live.setHidden(false);
    expect(live.polling).toBe(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(vi.mocked(fetchFleet).mock.calls.length).toBeGreaterThan(whileHidden);

    live.stop();
    expect(live.polling).toBe(false);
    vi.useRealTimers();
  });

  it('is idempotent, so repeated visibility events do not stack timers', async () => {
    vi.useFakeTimers();
    const live = new LiveFleet();
    live.start();
    live.setHidden(false); // already visible -> no-op
    live.setHidden(false);
    const before = vi.mocked(fetchFleet).mock.calls.length;
    await vi.advanceTimersByTimeAsync(5_000);
    // Exactly one poll fired in one interval: the timers were not duplicated.
    expect(vi.mocked(fetchFleet).mock.calls.length).toBe(before + 1);
    live.stop();
    vi.useRealTimers();
  });
});
