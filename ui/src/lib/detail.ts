// Builds the rows the Side Data Panel shows for any selectable entity (system,
// body, place). Pure — keeps the panel a dumb renderer and the shaping testable.

import type {
  FleetEntry,
  Place,
  ShipCatalogEntry,
  ShipState,
  System,
  SystemBody,
  SystemDetail
} from './api';

function whenShort(iso: string | null): string {
  return iso ? iso.replace('T', ' ').slice(0, 16) : '—';
}

const AU_PER_LY = 63241.077;

// "0.382c" in n-space; in hyper "0.382c real · 1640c apparent (Zeta)" — velocity is
// the apparent speed there, real = apparent / band multiplier (Sprint 031, #72).
function velocityText(s: ShipState): string {
  const apparent = s.velocity.fraction_c;
  if (s.band && s.band.velocity_multiplier > 0) {
    const real = apparent / s.band.velocity_multiplier;
    const band = s.band.name ?? `band ${s.band.order}`;
    return `${real.toFixed(3)}c real · ${Math.round(apparent).toLocaleString()}c apparent (${band})`;
  }
  return `${apparent.toFixed(3)}c`;
}

function distanceText(km: number | null): string {
  if (km == null) return '—';
  const au = km / 1.495978707e8;
  return au >= 1000 ? `${(au / AU_PER_LY).toFixed(2)} ly` : `${au.toFixed(2)} AU`;
}

// Rich ship detail from the live state endpoint (+ catalog for class/nation).
// Falls back via shipRows when /state is unavailable.
export function shipStateRows(s: ShipState, e: FleetEntry, ship?: ShipCatalogEntry | null): Detail {
  const rows: [string, string][] = [
    ['transponder', s.transponder ?? e.transponder],
    ['phase', s.phase],
    ['location', s.system ?? '(interstellar)'],
    ['destination', s.destination ?? '—'],
    ['ETA', whenShort(s.eta)],
    ['progress', s.percent_complete != null ? `${Math.round(s.percent_complete * 100)}%` : '—'],
    ['velocity', velocityText(s)]
  ];
  if (s.distance_to_destination_km != null) {
    rows.push(['to destination', distanceText(s.distance_to_destination_km)]);
  }
  if (s.queue_position != null) rows.push(['queue', `#${s.queue_position}`]);
  if (ship?.ship_class) rows.push(['class', ship.ship_class]);
  rows.push(['nation', ship?.nation_code ?? (s.transponder ?? e.transponder).split('.')[0]]);
  return { title: e.ship, kind: 'ship', rows };
}

export function shipRows(e: FleetEntry): Detail {
  const rows: [string, string][] = [
    ['transponder', e.transponder],
    ['phase', e.phase],
    ['location', e.system ?? '(interstellar)'],
    ['ETA', whenShort(e.eta)],
    ['progress', e.percent_complete != null ? `${Math.round(e.percent_complete * 100)}%` : '—']
  ];
  if (e.queue_position != null) rows.push(['queue', `#${e.queue_position}`]);
  return { title: e.ship, kind: 'ship', rows };
}

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
