import { describe, expect, it } from 'vitest';
import { phaseStyle } from './phase';

describe('phaseStyle', () => {
  it('maps known phases to distinct glyphs + labels', () => {
    expect(phaseStyle('hyper_cruise').glyph).toBe('✦');
    expect(phaseStyle('queued').glyph).toBe('⧖');
    expect(phaseStyle('arrived').glyph).toBe('●');
    expect(phaseStyle('transit').label).toMatch(/n-space/);
  });

  it('falls back for an unknown phase, echoing it in the label', () => {
    const s = phaseStyle('weird');
    expect(s.glyph).toBe('·');
    expect(s.label).toBe('weird');
  });
});
