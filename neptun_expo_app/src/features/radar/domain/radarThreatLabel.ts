/** Flutter `radar_threat_label.dart` parity */
export function radarThreatTypeLabel(type: string): string {
  switch (type.toLowerCase()) {
    case 'shahed':
    case 'drone':
      return 'Ударні БПЛА';
    case 'raketa':
    case 'missile':
      return 'Крилаті ракети';
    case 'ballistic':
      return 'Балістика';
    case 'avia':
      return 'Авіація';
    case 'kab':
      return 'КАБ';
    default:
      return 'Загроза';
  }
}
