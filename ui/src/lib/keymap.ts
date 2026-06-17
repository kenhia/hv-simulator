// Single source of truth for keyboard shortcuts. Reserve the full map now so later
// sprints don't collide; only `active` bindings are wired this sprint. Avoid the
// browser-captured function keys (F1/F3/F5/F6/F11/F12) and Ctrl/Cmd combos.

export type Action =
  | 'enter' // drill into the selected system
  | 'exit' // back out of the system scene / dismiss panel
  | 'zone' // toggle zone mode (center + clamp)
  | 'fit' // fit / reset view
  | 'search' // focus locate-a-ship (023)
  | 'layers' // layer toggles (023/025)
  | 'menu' // main menu (025)
  | 'playPause' // dev time scrubber (025)
  | 'stepBack'
  | 'stepForward';

export interface Binding {
  key: string; // KeyboardEvent.key
  action: Action;
  label: string;
  sprint: string;
  active: boolean; // wired this sprint?
}

export const KEYMAP: Binding[] = [
  { key: 'Enter', action: 'enter', label: 'enter selected system', sprint: '022', active: true },
  { key: 'Escape', action: 'exit', label: 'back out / dismiss', sprint: '022', active: true },
  { key: 'z', action: 'zone', label: 'toggle zone mode', sprint: '022', active: true },
  { key: 'f', action: 'fit', label: 'fit / reset view', sprint: '022', active: true },
  { key: '/', action: 'search', label: 'locate a ship', sprint: '023', active: false },
  { key: 'l', action: 'layers', label: 'layer toggles', sprint: '023/025', active: false },
  { key: 'm', action: 'menu', label: 'main menu', sprint: '025', active: false },
  { key: ' ', action: 'playPause', label: 'play/pause clock', sprint: '025', active: false },
  { key: ',', action: 'stepBack', label: 'step clock back', sprint: '025', active: false },
  { key: '.', action: 'stepForward', label: 'step clock forward', sprint: '025', active: false }
];

// Minimal shape so this is unit-testable without a DOM KeyboardEvent.
export interface KeyLike {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
}

export function actionForKey(e: KeyLike): Action | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null;
  const b = KEYMAP.find((b) => b.active && b.key === e.key);
  return b ? b.action : null;
}
