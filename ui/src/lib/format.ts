// Small pure formatters (unit-tested).

// Countdown text from a target instant to now (both epoch ms). Clamps at 0
// ("transiting"); MM:SS under an hour, else H:MM:SS.
export function etaText(targetMs: number, nowMs: number): string {
  const secs = Math.max(0, Math.round((targetMs - nowMs) / 1000));
  if (secs === 0) return 'transiting';
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
