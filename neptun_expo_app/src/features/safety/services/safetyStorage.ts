import { PrefsKeys } from '../../../config/prefsKeys';
import { persistentStorage } from '../../../services/persistentStorage';

export type MedicalCard = {
  bloodType: string;
  allergies: string;
  medications: string;
  emergencyContact1: string;
  emergencyContact2: string;
};

export const safetyStorage = {
  loadMedicalCard(): MedicalCard {
    return {
      bloodType: persistentStorage.getString(PrefsKeys.medicalBloodType) ?? '',
      allergies: persistentStorage.getString(PrefsKeys.medicalAllergies) ?? '',
      medications: persistentStorage.getString(PrefsKeys.medicalMedications) ?? '',
      emergencyContact1: persistentStorage.getString(PrefsKeys.emergencyContact1) ?? '',
      emergencyContact2: persistentStorage.getString(PrefsKeys.emergencyContact2) ?? '',
    };
  },

  saveMedicalCard(card: MedicalCard): void {
    persistentStorage.setString(PrefsKeys.medicalBloodType, card.bloodType);
    persistentStorage.setString(PrefsKeys.medicalAllergies, card.allergies);
    persistentStorage.setString(PrefsKeys.medicalMedications, card.medications);
    persistentStorage.setString(PrefsKeys.emergencyContact1, card.emergencyContact1);
    persistentStorage.setString(PrefsKeys.emergencyContact2, card.emergencyContact2);
  },

  loadEmergencyBag(): Record<string, boolean> {
    const raw = persistentStorage.getString(PrefsKeys.emergencyBagItems);
    if (!raw) return {};
    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      const out: Record<string, boolean> = {};
      for (const [k, v] of Object.entries(parsed)) {
        out[k] = Boolean(v);
      }
      return out;
    } catch {
      return {};
    }
  },

  saveEmergencyBag(items: Record<string, boolean>): void {
    persistentStorage.setString(PrefsKeys.emergencyBagItems, JSON.stringify(items));
  },
};
