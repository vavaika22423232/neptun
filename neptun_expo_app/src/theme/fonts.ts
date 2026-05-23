import { Platform } from 'react-native';

const webFallback = '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif';

function font(name: string) {
  return Platform.OS === 'web' ? `${name}, ${webFallback}` : name;
}

/** Native values must match `useFonts` keys in `app/_layout.tsx`. */
export const fonts = {
  regular: font('PlusJakartaSans_400Regular'),
  medium: font('PlusJakartaSans_500Medium'),
  semiBold: font('PlusJakartaSans_600SemiBold'),
  bold: font('PlusJakartaSans_700Bold'),
} as const;
