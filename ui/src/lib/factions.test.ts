import { describe, expect, it } from 'vitest';
import { factionColor, factionName } from './factions';

describe('factions', () => {
  it('maps a transponder to its nation by the first component', () => {
    expect(factionName('347.5.3')).toBe('Manticore (SK)');
    expect(factionName('618.1.1')).toBe('Haven');
    expect(factionColor('347.5.3')).toBe('#ff6b6b');
  });
  it('treats null / unknown codes gracefully', () => {
    expect(factionName(null)).toBe('Unaffiliated'); // code 0
    expect(factionName('9999.1.1')).toBe('Unknown');
    expect(factionColor('9999.1.1')).toBe('#cfd8e8');
  });
});
