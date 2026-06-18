import { describe, expect, it } from 'vitest';
import { nationName } from './nation';

describe('nationName', () => {
  it('maps known transponder nation codes to names', () => {
    expect(nationName('618')).toBe('Haven');
    expect(nationName('347')).toBe('Manticore');
    expect(nationName('1')).toBe('Solarian League');
    expect(nationName('734')).toBe('Andermani');
  });
  it('falls back for an unknown code', () => {
    expect(nationName('999')).toBe('Nation 999');
  });
});
