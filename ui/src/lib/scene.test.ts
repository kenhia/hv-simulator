import { describe, expect, it } from 'vitest';
import { actionForKey } from './keymap';
import { breadcrumb, GALAXY, type Scene } from './scene';

describe('breadcrumb', () => {
  const sol: Scene = { kind: 'system', id: 'sol' };
  it('reads "Galaxy" at the top', () => {
    expect(breadcrumb(GALAXY, null, null)).toBe('Galaxy');
  });
  it('shows the system name in a system', () => {
    expect(breadcrumb(sol, 'Sol', null)).toBe('Sol');
  });
  it('appends the focused body', () => {
    expect(breadcrumb(sol, 'Sol', 'Earth')).toBe('Sol / Earth');
  });
  it('falls back to the id when the name is unknown', () => {
    expect(breadcrumb(sol, null, null)).toBe('sol');
  });
});

describe('keymap', () => {
  it('maps the wired 022 keys', () => {
    expect(actionForKey({ key: 'Enter' })).toBe('enter');
    expect(actionForKey({ key: 'Escape' })).toBe('exit');
    expect(actionForKey({ key: 'z' })).toBe('zone');
    expect(actionForKey({ key: 'f' })).toBe('fit');
  });
  it('maps the flight-planner key, ignores reserved-but-inactive ones', () => {
    expect(actionForKey({ key: 'm' })).toBe('menu');
    expect(actionForKey({ key: '/' })).toBeNull(); // still reserved/inactive
  });
  it('ignores modifier combos (browser/OS shortcuts)', () => {
    expect(actionForKey({ key: 'f', ctrlKey: true })).toBeNull();
    expect(actionForKey({ key: 'f', metaKey: true })).toBeNull();
  });
});
