/**
 * Coalesce bursty marker_new SSE events without dropping map state.
 *
 * One marker can be delivered as a cheap delta. Multiple markers in the same
 * debounce window should trigger a refetch, otherwise a last-wins debounce loses
 * intermediate threats.
 */

export type MarkerSseEvent =
  | { type: 'marker_new'; data: Record<string, unknown> }
  | { type: 'markers_refresh'; data: { batch: true; count: number } };

export function coalesceMarkerNewEvents(markers: Record<string, unknown>[]): MarkerSseEvent | null {
  if (markers.length === 0) return null;
  if (markers.length === 1) {
    return { type: 'marker_new', data: markers[0] };
  }
  return {
    type: 'markers_refresh',
    data: { batch: true, count: markers.length },
  };
}
