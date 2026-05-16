import { Ionicons } from '@expo/vector-icons';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { CHAT_THEMES, chatThemeById, CHAT_THEME_DEFAULT_ID } from '../config/chatThemes';
import { AppConstants } from '../config/constants';
import { useApp } from '../context/AppContext';
import type { RootStackParamList } from '../navigation/types';
import { storage } from '../services/storage';
import { fonts } from '../theme/fonts';

/** Mirrors Flutter `PremiumPaywallStyle.dark` essentials. */
const P = {
  bgMid: '#0A0E18',
  textPrimary: '#F2F4F8',
  textSecondary: '#9AA3B2',
  textTertiary: '#6B7280',
  accent: '#D4B060',
  accentDeep: '#7A5C20',
  panel: 'rgba(255,255,255,0.06)',
  panelBorder: 'rgba(255,255,255,0.08)',
  hairline: 'rgba(255,255,255,0.07)',
  chromeIcon: '#E8D5A8',
};

const PANEL_RADIUS = 22;

export function PremiumScreen() {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { isPremium, setPremium } = useApp();
  const [themeId, setThemeIdState] = useState(CHAT_THEME_DEFAULT_ID);
  const [animAvatar, setAnimAvatarState] = useState(false);
  const [themeModal, setThemeModal] = useState(false);

  const refreshPrefs = useCallback(async () => {
    const tid = (await storage.getProChatThemeId()) || CHAT_THEME_DEFAULT_ID;
    setThemeIdState(chatThemeById(tid).id);
    setAnimAvatarState(await storage.getProAnimatedAvatar());
  }, []);

  useEffect(() => {
    void refreshPrefs();
  }, [refreshPrefs]);

  function goProfileSoundSection() {
    navigation.navigate('MainTabs', { screen: 'Profile' });
    navigation.goBack();
  }

  const selectedTheme = chatThemeById(themeId);

  const memberPanel = (
    <View style={[styles.panel, { borderColor: P.panelBorder }]}>
      <SectionLabel>Оформлення</SectionLabel>
      <MemberTile
        icon="color-palette"
        title="Тема чату"
        subtitle={selectedTheme.label}
        onPress={() => setThemeModal(true)}
      />
      <Hairline />
      <MemberTile
        icon="scan-outline"
        title="Анімована аватарка"
        subtitle={animAvatar ? 'Увімкнено в чаті' : 'Вимкнено'}
        trailing={
          <Switch
            value={animAvatar}
            onValueChange={(v) => {
              setAnimAvatarState(v);
              void storage.setProAnimatedAvatar(v);
            }}
            trackColor={{ false: P.hairline, true: P.accent + '55' }}
            thumbColor={animAvatar ? P.accent : P.textTertiary}
          />
        }
      />
      <Hairline />
      <SectionLabel>Функції</SectionLabel>
      <MemberTile
        icon="time"
        title="Історія тривог"
        subtitle="Журнал загроз"
        onPress={() => navigation.navigate('AlarmHistory')}
      />
      <Hairline />
      <MemberTile
        icon="bar-chart"
        title="Аналітика"
        subtitle="Час під тривогою"
        onPress={() => navigation.navigate('PersonalAnalytics')}
      />
      <Hairline />
      <MemberTile
        icon="flame"
        title="Теплова карта"
        subtitle="Активність по регіонах"
        onPress={() => navigation.navigate('Heatmap')}
      />
      <Hairline />
      <MemberTile
        icon="moon"
        title="Режим сну"
        subtitle="Налаштування сповіщень вночі"
        onPress={() => navigation.navigate('SleepMode')}
      />
      <Hairline />
      <MemberTile
        icon="volume-high"
        title="Звук тривоги"
        subtitle="У профілі"
        onPress={goProfileSoundSection}
      />
    </View>
  );

  const paywallBody = (
    <>
      <Text style={styles.price}>{AppConstants.premiumDisplayPrice}</Text>
      <Text style={styles.priceSub}>щомісячна підписка · скасуйте будь-коли</Text>
      <Text style={styles.trust}>• щомісячна підписка · скасуйте будь-коли · миттєвий доступ</Text>
      <Text style={styles.whatsIn}>ЩО ВХОДИТЬ</Text>
      <View style={[styles.panel, { borderColor: P.panelBorder }]}>
        {[
          ['Точні сповіщення по районах', 'location'],
          ['Режим сну та фільтри нічних тривог', 'moon'],
          ['Історія тривог і аналітика', 'analytics'],
          ['Теплова карта та теми чату', 'flame'],
          ['Без реклами та розширений радар', 'rocket-outline'],
        ].map(([label, icon], i, arr) => (
          <View key={label}>
            <View style={styles.featureRow}>
              <Ionicons name={icon as React.ComponentProps<typeof Ionicons>['name']} size={20} color={P.accent} />
              <Text style={styles.featureTxt}>{label}</Text>
            </View>
            {i < arr.length - 1 ? <Hairline /> : null}
          </View>
        ))}
      </View>
      <Text style={styles.legal}>
        Оплата через Apple або Google. Підписку можна скасувати будь-коли в налаштуваннях магазину.
      </Text>
      <Text style={styles.devNote}>
        У цій збірці також доступне локальне вмикання PRO для перевірки екранів — нативний IAP буде підключено
        окремо.
      </Text>
    </>
  );

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <LinearGradient
        colors={[P.bgMid, '#060912']}
        style={StyleSheet.absoluteFill}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
      />

      <View style={styles.topBar}>
        <Pressable onPress={() => navigation.goBack()} style={styles.iconBtn}>
          <Ionicons name="close" size={24} color={P.chromeIcon} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + (isPremium ? 24 : 120) }]}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <LinearGradient colors={[P.accent + '55', P.accentDeep + '33']} style={styles.heroRingOut}>
            <View style={styles.heroRingIn}>
              <Ionicons name="sparkles" size={38} color={P.accent} />
            </View>
          </LinearGradient>
          <Text style={styles.heroTitle}>{isPremium ? 'Ви з PRO' : `${AppConstants.appName} PRO`}</Text>
          <Text style={styles.heroSub}>
            {isPremium
              ? 'Дякуємо за довіру — налаштуйте оформлення нижче.'
              : 'Повний радар, детальні сповіщення, режим сну та спокій без зайвого шуму.'}
          </Text>
        </View>

        {isPremium ? memberPanel : paywallBody}
      </ScrollView>

      {!isPremium ? (
        <View style={[styles.sticky, { paddingBottom: insets.bottom + 12 }]}>
          <PrimaryButton onPress={() => void setPremium(true)}>Увімкнути локальний PRO</PrimaryButton>
        </View>
      ) : null}

      <Modal visible={themeModal} animationType="fade" transparent>
        <Pressable style={styles.modalBackdrop} onPress={() => setThemeModal(false)}>
          <Pressable
            style={[styles.modalCard, { borderColor: P.panelBorder }]}
            onPress={(e) => e.stopPropagation()}
          >
            <Text style={styles.modalTitle}>Тема чату</Text>
            {CHAT_THEMES.map((t) => (
              <Pressable
                key={t.id}
                style={[styles.themeRow, themeId === t.id && styles.themeRowOn]}
                onPress={() => {
                  setThemeIdState(t.id);
                  void storage.setProChatThemeId(t.id);
                  setThemeModal(false);
                }}
              >
                <View style={[styles.themeSwatch, { backgroundColor: t.bubbleTint || P.textTertiary }]} />
                <Text style={styles.themeLabel}>{t.label}</Text>
                {themeId === t.id ? <Ionicons name="checkmark-circle" size={22} color={P.accent} /> : null}
              </Pressable>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

function SectionLabel({ children }: { children: string }) {
  return <Text style={styles.sectionLabel}>{children.toUpperCase()}</Text>;
}

function Hairline() {
  return <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: P.hairline }} />;
}

function MemberTile({
  icon,
  title,
  subtitle,
  onPress,
  trailing,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  title: string;
  subtitle: string;
  onPress?: () => void;
  trailing?: React.ReactNode;
}) {
  const row = (
    <View style={styles.tile}>
      <Ionicons name={icon} size={22} color={P.accent} />
      <View style={{ flex: 1, marginLeft: 14 }}>
        <Text style={styles.tileTitle}>{title}</Text>
        <Text style={styles.tileSub}>{subtitle}</Text>
      </View>
      {trailing ?? <Ionicons name="chevron-forward" size={22} color={P.textTertiary} />}
    </View>
  );
  if (trailing) return row;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => pressed && { opacity: 0.92 }}>
      {row}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: P.bgMid },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingBottom: 8,
  },
  iconBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: P.panel,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: P.panelBorder,
  },
  scroll: { paddingHorizontal: 22 },
  hero: { alignItems: 'center', paddingBottom: 10 },
  heroRingOut: {
    width: 94,
    height: 94,
    borderRadius: 47,
    padding: 3,
    marginBottom: 22,
  },
  heroRingIn: {
    flex: 1,
    borderRadius: 44,
    backgroundColor: 'rgba(10,14,24,0.94)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroTitle: {
    fontFamily: fonts.bold,
    fontSize: 30,
    color: P.textPrimary,
    textAlign: 'center',
    letterSpacing: -0.6,
  },
  heroSub: {
    marginTop: 12,
    fontFamily: fonts.medium,
    fontSize: 16,
    lineHeight: 23,
    color: P.textSecondary,
    textAlign: 'center',
    paddingHorizontal: 8,
  },
  panel: {
    borderRadius: PANEL_RADIUS,
    backgroundColor: P.panel,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
  },
  sectionLabel: {
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 6,
    fontFamily: fonts.bold,
    fontSize: 11,
    letterSpacing: 1.4,
    color: P.textTertiary,
  },
  tile: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  tileTitle: {
    fontFamily: fonts.semiBold,
    fontSize: 15,
    color: P.textPrimary,
  },
  tileSub: {
    marginTop: 2,
    fontFamily: fonts.regular,
    fontSize: 12,
    color: P.textSecondary,
    lineHeight: 16,
  },
  price: {
    marginTop: 8,
    fontFamily: fonts.bold,
    fontSize: 42,
    color: P.accent,
    textAlign: 'center',
    letterSpacing: -1,
  },
  priceSub: {
    fontFamily: fonts.semiBold,
    fontSize: 14,
    color: P.textSecondary,
    textAlign: 'center',
    marginBottom: 18,
  },
  trust: {
    fontFamily: fonts.semiBold,
    fontSize: 12,
    letterSpacing: 0.35,
    color: P.textTertiary,
    textAlign: 'center',
    marginBottom: 26,
  },
  whatsIn: {
    fontFamily: fonts.bold,
    fontSize: 13,
    letterSpacing: 2,
    color: P.textTertiary,
    marginBottom: 14,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  featureTxt: {
    flex: 1,
    fontFamily: fonts.medium,
    fontSize: 14,
    color: P.textPrimary,
    lineHeight: 20,
  },
  legal: {
    marginTop: 16,
    fontFamily: fonts.medium,
    fontSize: 12,
    lineHeight: 18,
    color: P.textTertiary,
    textAlign: 'center',
  },
  devNote: {
    marginTop: 14,
    marginBottom: 12,
    fontFamily: fonts.regular,
    fontSize: 12,
    lineHeight: 17,
    color: P.textTertiary,
    textAlign: 'center',
    opacity: 0.85,
  },
  sticky: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 22,
    paddingTop: 12,
    backgroundColor: 'rgba(6,9,14,0.94)',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: P.panelBorder,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center',
    paddingHorizontal: 28,
  },
  modalCard: {
    borderRadius: PANEL_RADIUS,
    backgroundColor: '#121722',
    borderWidth: StyleSheet.hairlineWidth,
    paddingVertical: 8,
    maxHeight: '72%',
  },
  modalTitle: {
    fontFamily: fonts.bold,
    fontSize: 17,
    color: P.textPrimary,
    paddingHorizontal: 18,
    paddingVertical: 14,
  },
  themeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: P.hairline,
  },
  themeRowOn: { backgroundColor: 'rgba(212,176,96,0.08)' },
  themeSwatch: {
    width: 28,
    height: 28,
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: P.panelBorder,
  },
  themeLabel: {
    flex: 1,
    fontFamily: fonts.medium,
    fontSize: 15,
    color: P.textPrimary,
  },
});
