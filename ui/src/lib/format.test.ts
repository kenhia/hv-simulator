import { describe, expect, it } from 'vitest';
import { etaText } from './format';

describe('etaText', () => {
  it('formats MM:SS under an hour', () => {
    expect(etaText(12_000, 0)).toBe('00:12');
    expect(etaText(90_000, 0)).toBe('01:30');
  });
  it('formats H:MM:SS at an hour or more', () => {
    expect(etaText(3_661_000, 0)).toBe('1:01:01');
  });
  it('clamps past-due to "transiting"', () => {
    expect(etaText(0, 5000)).toBe('transiting');
    expect(etaText(1000, 1000)).toBe('transiting');
  });
});
