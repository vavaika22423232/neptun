import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { memo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { AppText } from '../../../components/ui/AppText';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

type Item = {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  hint?: string;
  pro?: boolean;
  onPress: () => void;
};

type Props = {
  visible: boolean;
  onClose: () => void;
  items: Item[];
};

function MapMoreSheetInner({ visible, onClose, items }: Props) {
  const { theme } = useAppTheme();
  const styles = useSheetStyles();

  return (
    <NeptunBottomSheet visible={visible} onClose={onClose} maxHeightRatio={0.42}>
      <AppText variant="sectionTitle" style={styles.title}>
        Дії
      </AppText>
      {items.map((item, index) => (
        <Pressable
          key={item.label}
          onPress={() => {
            onClose();
            item.onPress();
          }}
          style={[styles.row, index < items.length - 1 && styles.rowBorder]}
        >
          <View
            style={[
              styles.icon,
              {
                backgroundColor: item.pro ? theme.colors.proSoft : theme.colors.surfaceSoft,
              },
            ]}
          >
            <Ionicons
              name={item.icon}
              size={20}
              color={item.pro ? theme.colors.pro : theme.colors.textSecondary}
            />
          </View>
          <View style={styles.copy}>
            <AppText variant="cardTitle">{item.label}</AppText>
            {item.hint ? (
              <AppText variant="meta" muted>
                {item.hint}
              </AppText>
            ) : null}
          </View>
          <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
        </Pressable>
      ))}
    </NeptunBottomSheet>
  );
}

function useSheetStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      title: { marginBottom: t.spacing.md },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingVertical: 14,
        minHeight: 56,
      },
      rowBorder: {
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.divider,
      },
      icon: {
        width: 40,
        height: 40,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
      },
      copy: { flex: 1, gap: 2 },
    }),
  );
}

export const MapMoreSheet = memo(MapMoreSheetInner);
