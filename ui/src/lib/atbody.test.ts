import { describe, expect, it } from 'vitest';
import { AT_BODY_PHASES, atBodyGroups } from './atbody';

const bodies = [
  { id: 'medusa', x: 1, y: 0 },
  { id: 'gryphon', x: -3, y: 2 }
];

describe('atBodyGroups', () => {
  it('groups ships by the nearest body within tolerance, preserving order', () => {
    const g = atBodyGroups(
      [
        { id: '213.2.1', x: 1.0, y: 0.0 },
        { id: '213.2.3', x: 1.01, y: -0.01 },
        { id: '347.1.1', x: -3.0, y: 2.0 }
      ],
      bodies
    );
    expect(g.get('medusa')).toEqual(['213.2.1', '213.2.3']);
    expect(g.get('gryphon')).toEqual(['347.1.1']);
  });

  it('omits ships with no body in range', () => {
    const g = atBodyGroups([{ id: 'x', x: 50, y: 50 }], bodies);
    expect(g.size).toBe(0);
  });

  it('knows the at-rest phases', () => {
    expect(AT_BODY_PHASES.has('arrived')).toBe(true);
    expect(AT_BODY_PHASES.has('layover')).toBe(true);
    expect(AT_BODY_PHASES.has('hyper_cruise')).toBe(false);
    expect(AT_BODY_PHASES.has('queued')).toBe(false);
  });
});
