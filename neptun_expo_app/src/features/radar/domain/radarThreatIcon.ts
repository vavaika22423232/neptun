import type { ComponentProps } from 'react';
import type { Ionicons } from '@expo/vector-icons';

type IonName = ComponentProps<typeof Ionicons>['name'];

/** Flutter `radar_tab.dart` `_threatIcon`. */
export function radarThreatIconName(type: string): IonName {
  switch (type.toLowerCase()) {
    case 'shahed':
    case 'drone':
      return 'airplane';
    case 'raketa':
    case 'missile':
      return 'rocket';
    case 'ballistic':
      return 'warning';
    case 'avia':
      return 'airplane-outline';
    case 'kab':
      return 'locate';
    default:
      return 'alert-circle';
  }
}
