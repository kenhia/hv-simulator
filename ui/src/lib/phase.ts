// Phase → glyph/colour/label for the Fleet Board (Sprint 031). A compact leading
// glyph replaces the old phase+ETA text columns so the ship name gets the row.
// Colours echo the ShipTimeline segment palette; the label is the tooltip text.

export interface PhaseStyle {
  glyph: string;
  color: string;
  label: string;
}

const PHASE_STYLE: Record<string, PhaseStyle> = {
  predeparture: { glyph: '○', color: '#6b7689', label: 'at origin (pre-departure)' },
  idle: { glyph: '○', color: '#6b7689', label: 'idle' },
  transit: { glyph: '▸', color: '#5b7bb5', label: 'in transit (n-space)' },
  hyper_cruise: { glyph: '✦', color: '#9a7bd0', label: 'hyperspace cruise' },
  layover: { glyph: '‖', color: '#5aa06e', label: 'layover' },
  queued: { glyph: '⧖', color: '#caa64a', label: 'queued at a wormhole junction' },
  wormhole_transit: { glyph: '⊚', color: '#d0a44a', label: 'wormhole transit' },
  arrived: { glyph: '●', color: '#8aa0c0', label: 'arrived' }
};

const FALLBACK: PhaseStyle = { glyph: '·', color: '#888', label: 'unknown' };

export function phaseStyle(phase: string): PhaseStyle {
  return PHASE_STYLE[phase] ?? { ...FALLBACK, label: phase || 'unknown' };
}
