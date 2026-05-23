import type { ComponentProps } from 'react';
import type { Ionicons } from '@expo/vector-icons';

/** Flutter `safety_page.dart` `_emergencyBagChecklist`. */
export type EmergencyBagItem = {
  key: string;
  name: string;
  icon: ComponentProps<typeof Ionicons>['name'];
};

export const EMERGENCY_BAG_CHECKLIST: EmergencyBagItem[] = [
  { key: 'documents', name: 'Документи', icon: 'card' },
  { key: 'water', name: 'Вода (2л на особу)', icon: 'water' },
  { key: 'food', name: 'Консерви/їжа (3 дні)', icon: 'restaurant' },
  { key: 'flashlight', name: 'Ліхтарик + батарейки', icon: 'flashlight' },
  { key: 'powerbank', name: 'Powerbank', icon: 'battery-charging' },
  { key: 'firstaid', name: 'Аптечка', icon: 'medkit' },
  { key: 'cash', name: 'Готівка', icon: 'cash' },
  { key: 'clothes', name: 'Змінний одяг', icon: 'shirt' },
  { key: 'blanket', name: 'Ковдра/плед', icon: 'bed' },
  { key: 'radio', name: 'Радіо на батарейках', icon: 'radio' },
  { key: 'charger', name: 'Зарядки для телефону', icon: 'git-branch' },
  { key: 'hygiene', name: 'Засоби гігієни', icon: 'sparkles' },
];
