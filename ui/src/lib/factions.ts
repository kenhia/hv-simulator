// Faction colours keyed on the transponder's nation code (its first component,
// from data/transponder-codes.json). A fixed default palette for now;
// user-remappable schemes are deferred (planning/007) — keep this the one seam.

interface Faction {
  name: string;
  color: string;
}

const FACTIONS: Record<string, Faction> = {
  '0': { name: 'Unaffiliated', color: '#9aa6bd' },
  '1': { name: 'Solarian League', color: '#9fd0ff' },
  '2': { name: 'Beowulf', color: '#7fd0a0' },
  '213': { name: 'Grayson', color: '#cdb4ff' },
  '347': { name: 'Manticore (SK)', color: '#ff6b6b' },
  '419': { name: 'Manticore (SE)', color: '#ff9d4d' },
  '489': { name: 'Masada', color: '#b08a3a' },
  '555': { name: 'Silesia', color: '#caa64a' },
  '618': { name: 'Haven', color: '#5b8aff' }
};

const FALLBACK: Faction = { name: 'Unknown', color: '#cfd8e8' };

function lookup(transponder: string | null): Faction {
  const code = transponder ? transponder.split('.')[0] : '0';
  return FACTIONS[code] ?? FALLBACK;
}

export function factionColor(transponder: string | null): string {
  return lookup(transponder).color;
}

export function factionName(transponder: string | null): string {
  return lookup(transponder).name;
}
