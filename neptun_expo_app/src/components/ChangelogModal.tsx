import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Modal, Pressable, StyleSheet, View } from 'react-native';
import type { ChangelogItem } from '../config/changelog';
import { AppConstants } from '../config/constants';
import { palette, radii, spacing } from '../design/tokens';
import { colors } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';
import { PrimaryButton } from './PrimaryButton';
import { Text } from './Text';

type Props = {
  visible: boolean;
  items: ChangelogItem[];
  onDismiss: () => void;
};

function itemIcon(name: ChangelogItem['icon']): keyof typeof Ionicons.glyphMap {
  switch (name) {
    case 'cloud-offline':
      return 'cloud-offline';
    case 'camera':
      return 'camera';
    case 'moon':
      return 'moon';
    default:
      return 'sparkles';
  }
}

/** Flutter `ChangelogDialog` — gradient modal, non-dismissible barrier. */
export function ChangelogModal({ visible, items, onDismiss }: Props) {
  const styles = useScreenStyles();
return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onDismiss}>
      <View style={styles.backdrop}>
        <View style={styles.cardWrap}>
          <LinearGradient
            colors={[palette.bg, palette.bgElevated, palette.surfaceRaised]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.gradient}
          >
            <View style={styles.header}>
              <View style={styles.iconCircle}>
                <Ionicons name="sparkles" size={32} color={colors.text} />
              </View>
              <Text style={styles.title}>Що нового?</Text>
              <View style={styles.versionPill}>
                <Text style={styles.versionText}>Версія {AppConstants.appVersion}</Text>
              </View>
            </View>

            <View style={styles.list}>
              {items.map((item) => (
                <View key={item.title} style={styles.row}>
                  <View style={[styles.itemIcon, { backgroundColor: item.iconColor + '1A' }]}>
                    <Ionicons name={itemIcon(item.icon)} size={20} color={item.iconColor} />
                  </View>
                  <View style={styles.itemText}>
                    <Text style={styles.itemTitle}>{item.title}</Text>
                    <Text muted style={styles.itemDesc}>
                      {item.description}
                    </Text>
                  </View>
                </View>
              ))}
            </View>

            <View style={styles.btnWrap}>
              <PrimaryButton onPress={onDismiss}>Зрозуміло!</PrimaryButton>
            </View>
          </LinearGradient>
        </View>
      </View>
    </Modal>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.65)',
    justifyContent: 'center',
    padding: 24,
  },
  cardWrap: {
    maxWidth: 400,
    width: '100%',
    alignSelf: 'center',
    borderRadius: 24,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOpacity: 0.4,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 12 },
    elevation: 12,
  },
  gradient: {
    paddingBottom: 16,
  },
  header: {
    alignItems: 'center',
    paddingTop: 20,
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  iconCircle: {
    padding: 12,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.2)',
    marginBottom: 12,
  },
  title: {
    fontFamily: fonts.bold,
    fontSize: 22,
    color: c.text,
  },
  versionPill: {
    marginTop: 6,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  versionText: {
    fontFamily: fonts.semiBold,
    fontSize: 12,
    color: c.text,
  },
  list: {
    marginHorizontal: 12,
    padding: 14,
    borderRadius: 14,
    backgroundColor: c.bg,
    gap: 10,
  },
  row: {
    flexDirection: 'row',
    gap: 10,
  },
  itemIcon: {
    padding: 6,
    borderRadius: 8,
  },
  itemText: {
    flex: 1,
  },
  itemTitle: {
    fontFamily: fonts.bold,
    fontSize: 14,
    color: c.text,
  },
  itemDesc: {
    fontSize: 12,
    lineHeight: 16,
    marginTop: 2,
  },
  btnWrap: {
    marginHorizontal: 16,
    marginTop: 16,
  },
}));
}
