/// Локалізована назва типу загрози для Радару та спільних списків.
String radarThreatTypeLabel(String type) {
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
