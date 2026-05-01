/**
 * Strips bloat from `public/ukraine_states.svg` after parse — same file is shared with
 * desktop (full) and WebView / mobile (pruned). Keeps <g class="state"> and removes
 * defs and decorative overlays to reduce parse + paint cost on Android.
 */

const DECOR_GROUP_IDS = ['mig_mozdok', 'mig_savasleika', 'notification_boats', 'tactival_aviation'] as const;

/**
 * DOM-heavy decorations at the end of ukraine_states.svg (MIG sectors, etc.) + entire defs
 * block (patterns/gradients unused by `.stateObject` CSS fills). Dropped for embed / mobile.
 *
 * @param svg - Root `<svg>` from ukraine_states (clone, not the cached template)
 */
export function pruneUkraineStatesSvgForLowGpu(svg: SVGElement): void {
  for (const id of DECOR_GROUP_IDS) {
    svg.querySelector(`#${id}`)?.remove();
  }
  svg.querySelector('defs')?.remove();
  for (const el of svg.querySelectorAll('[onclick]')) {
    el.removeAttribute('onclick');
  }
}

/**
 * Precompute region id → elements with `.stateObject` (and id) for O(1) alarm toggles
 * instead of `querySelectorAll([id="…"])` on every alarm tick.
 *
 * @param svg - State overlay root `<svg>` (after optional prune)
 * @returns Map of region id → all matching path elements
 */
export function buildStateObjectIndex(svg: SVGElement): Map<string, Element[]> {
  const m = new Map<string, Element[]>();
  for (const el of svg.querySelectorAll('.stateObject[id]')) {
    const id = el.getAttribute('id');
    if (!id) continue;
    const cur = m.get(id);
    if (cur) cur.push(el);
    else m.set(id, [el]);
  }
  return m;
}

/**
 * @param svg - Districts overlay (full SVG)
 */
export function buildDistrictObjectIndex(svg: SVGElement): Map<string, Element[]> {
  const m = new Map<string, Element[]>();
  for (const el of svg.querySelectorAll('.dist[id]')) {
    const id = el.getAttribute('id');
    if (!id) continue;
    const cur = m.get(id);
    if (cur) cur.push(el);
    else m.set(id, [el]);
  }
  return m;
}
