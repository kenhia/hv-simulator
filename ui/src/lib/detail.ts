// Builds the rows the Side Data Panel shows for any selectable entity (system,
// body, place). Pure — keeps the panel a dumb renderer and the shaping testable.

import type { Place, System, SystemBody, SystemDetail } from './api';

export interface Detail {
  title: string;
  kind: string;
  rows: [string, string][];
}

export function systemDetailRows(d: SystemDetail): Detail {
  return {
    title: d.name,
    kind: 'system',
    rows: [
      ['id', d.id],
      ['nation', d.star_nation_id ?? '—'],
      ['type', d.is_binary ? 'binary' : 'single star'],
      ['stars', d.stars.map((s) => s.name ?? s.id).join(', ') || '—'],
      [
        'hyper limit',
        d.primary_hyper_limit_au != null ? `${d.primary_hyper_limit_au.toFixed(2)} AU` : '—'
      ],
      ['distance', d.distance_ly != null ? `${d.distance_ly.toFixed(1)} ly` : '—']
    ]
  };
}

export function systemRows(s: System): Detail {
  const c = s.coordinates;
  return {
    title: s.name,
    kind: 'system',
    rows: [
      ['id', s.id],
      ['nation', s.star_nation_id ?? '—'],
      ['type', s.is_binary ? 'binary' : 'single star'],
      ['distance', s.distance_ly != null ? `${s.distance_ly.toFixed(1)} ly` : '—'],
      ['galactic', c ? `${c.x_ly.toFixed(1)}, ${c.y_ly.toFixed(1)}, ${c.z_ly.toFixed(1)} ly` : '—']
    ]
  };
}

export function bodyRows(b: SystemBody): Detail {
  const au = b.position.au;
  return {
    title: b.name,
    kind: b.type ?? 'body',
    rows: [
      ['id', b.id],
      ['type', b.type ?? '—'],
      ['distance', `${b.position.distance_from_sun_au.toFixed(3)} AU`],
      ['position', `${au.x.toFixed(2)}, ${au.y.toFixed(2)} AU`]
    ]
  };
}

export function placeRows(p: Place): Detail {
  return {
    title: p.name ?? p.id,
    kind: p.type ?? 'place',
    rows: [
      ['id', p.id],
      ['type', p.type ?? '—'],
      ['rides on', p.rides_on_body_id ?? '— (free-floating)']
    ]
  };
}
