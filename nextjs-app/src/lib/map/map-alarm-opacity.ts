/** Вирази `fill-opacity` для oblast / district (без rgba в fill-color — зручно анімувати). */

export function oblastAlarmFillOpacityCase(hascs: string[], opacity: number): unknown[] {
  return ['case', ['in', ['get', 'HASC_1'], ['literal', hascs]], opacity, 0];
}

export function districtAlarmFillOpacityCase(ids: string[], opacity: number): unknown[] {
  return ['case', ['in', ['to-string', ['get', 'regionId']], ['literal', ids]], opacity, 0];
}
