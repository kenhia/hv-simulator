// Scene state for the LOD spine: the galaxy graph or one system's top-down. Pure
// helpers (no DOM) so the breadcrumb + transition logic are unit-testable.

export type Scene = { kind: 'galaxy' } | { kind: 'system'; id: string };

export const GALAXY: Scene = { kind: 'galaxy' };

// The At-a-glance breadcrumb: Galaxy -> <System> -> <System> / <Body>.
export function breadcrumb(
  scene: Scene,
  systemName: string | null,
  bodyName: string | null
): string {
  if (scene.kind === 'galaxy') return 'Galaxy';
  const sys = systemName ?? scene.id;
  return bodyName ? `${sys} / ${bodyName}` : sys;
}
