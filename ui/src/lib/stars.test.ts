import { describe, expect, it } from 'vitest';
import type { Position, Star, SystemBody } from './api';
import {
  bodyColor,
  DEFAULT_PLANET,
  MOON_COLOR,
  starColors,
  STAR_PALETTE,
  starWorld
} from './stars';

const pos = (x: number, y: number): Position => ({
  km: { x: x * 1.5e8, y: y * 1.5e8, z: 0 },
  au: { x, y, z: 0 },
  distance_from_sun_km: 0,
  distance_from_sun_au: 0
});

const star = (id: string, p: Position | null): Star => ({
  id,
  name: id,
  role: null,
  spectral_type: null,
  mass_solar: null,
  hyper_limit_lmin: null,
  position: p
});

const body = (parent: string | null, type = 'planet'): SystemBody => ({
  id: 'b',
  name: 'b',
  type,
  parent_star_id: parent,
  position: pos(1, 0)
});

describe('starColors', () => {
  it('assigns palette by order (primary first), stable', () => {
    const m = starColors([star('a', null), star('b', null)]);
    expect(m.get('a')).toBe(STAR_PALETTE[0]);
    expect(m.get('b')).toBe(STAR_PALETTE[1]);
    expect(m.get('a')).not.toBe(m.get('b'));
  });
});

describe('starWorld', () => {
  it('reads AU position; origin when absent', () => {
    expect(starWorld(star('a', pos(-33, -12)))).toEqual({ x: -33, y: -12 });
    expect(starWorld(star('a', null))).toEqual({ x: 0, y: 0 });
  });
});

describe('bodyColor', () => {
  const m = starColors([star('a', null), star('b', null)]);
  it('colours a planet by its parent star', () => {
    expect(bodyColor(body('a'), m)).toBe(STAR_PALETTE[0]);
    expect(bodyColor(body('b'), m)).toBe(STAR_PALETTE[1]);
  });
  it('moons stay neutral; unknown parent falls back', () => {
    expect(bodyColor(body('a', 'moon'), m)).toBe(MOON_COLOR);
    expect(bodyColor(body(null), m)).toBe(DEFAULT_PLANET);
  });
});
