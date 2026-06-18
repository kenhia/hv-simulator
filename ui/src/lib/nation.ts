// Transponder nation code → display name (Sprint 032). The transponder is
// nation.class.hull; its first component is the nation code (see
// data/transponder-codes.json). Used by the Fleet Board nation filter so it reads
// as names, not bare codes. Unknown codes fall back to "Nation <code>".

const NATION_NAME: Record<string, string> = {
  '0': 'Unaffiliated',
  '1': 'Solarian League',
  '2': 'Beowulf',
  '213': 'Grayson',
  '347': 'Manticore',
  '419': 'Manticore (Empire)',
  '489': 'Masada',
  '555': 'Silesia',
  '618': 'Haven',
  '661': 'Erewhon',
  '734': 'Andermani'
};

export function nationName(code: string): string {
  return NATION_NAME[code] ?? `Nation ${code}`;
}
