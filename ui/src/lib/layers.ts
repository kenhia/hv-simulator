// Map layer visibility flags (toggled by the `l` control).

export interface Layers {
  ships: boolean;
  labels: boolean;
  wormholes: boolean;
  ring: boolean;
  stations: boolean;
}

export const DEFAULT_LAYERS: Layers = {
  ships: true,
  labels: true,
  wormholes: true,
  ring: true,
  stations: true
};

// Order + human labels for the toggle UI.
export const LAYER_ROWS: [keyof Layers, string][] = [
  ['ships', 'ships'],
  ['labels', 'labels'],
  ['wormholes', 'wormhole links'],
  ['ring', 'hyper-limit ring'],
  ['stations', 'stations']
];
