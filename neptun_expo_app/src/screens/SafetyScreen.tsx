import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  TextInput,
  View,
} from 'react-native';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { Text } from '../components/Text';
import { RoutePaths } from '../core/navigation/routePaths';
import { EMERGENCY_BAG_CHECKLIST } from '../features/safety/constants/emergencyBagChecklist';
import { safetyStorage, type MedicalCard } from '../features/safety/services/safetyStorage';
import { radii, spacing } from '../theme/colors';
import { fonts } from '../theme/fonts';
import { useLegacyColors } from '../theme/useAppTheme';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

function ToolRow({
  icon,
  title,
  description,
  color,
  onPress,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  title: string;
  description: string;
  color: string;
  onPress: () => void;
}) {
  const styles = useScreenStyles();
  const c = useLegacyColors();
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.toolRow, pressed && styles.pressed]}>
      <View style={[styles.toolIcon, { backgroundColor: `${color}22` }]}>
        <Ionicons name={icon} size={22} color={color} />
      </View>
      <View style={styles.toolBody}>
        <Text style={styles.toolTitle}>{title}</Text>
        <Text muted style={styles.toolDesc}>
          {description}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={c.muted} />
    </Pressable>
  );
}

/** Flutter `SafetyPage` / `ToolsTab`. */
export function SafetyScreen() {
  const styles = useScreenStyles();
  const c = useLegacyColors();
  const router = useRouter();
  const [medical, setMedical] = useState<MedicalCard>(() => safetyStorage.loadMedicalCard());
  const [bag, setBag] = useState<Record<string, boolean>>(() => safetyStorage.loadEmergencyBag());
  const [medicalModal, setMedicalModal] = useState(false);
  const [contactsModal, setContactsModal] = useState(false);
  const [bagModal, setBagModal] = useState(false);
  const [draft, setDraft] = useState<MedicalCard>(medical);

  const reload = useCallback(() => {
    setMedical(safetyStorage.loadMedicalCard());
    setBag(safetyStorage.loadEmergencyBag());
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const bagChecked = Object.values(bag).filter(Boolean).length;
  const bagTotal = EMERGENCY_BAG_CHECKLIST.length;

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.pad}>
      <Pressable onPress={() => router.push(RoutePaths.shelters)} style={({ pressed }) => [styles.shelterHero, pressed && styles.pressed]}>
        <View style={styles.shelterIcon}>
          <Ionicons name="location" size={32} color={c.accent} />
        </View>
        <View style={styles.flex}>
          <Text style={styles.heroTitle}>Укриття поруч</Text>
          <Text muted style={styles.heroSub}>
            Знайти найближчі укриття та метро
          </Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={c.muted} />
      </Pressable>

      <Text style={styles.section}>Поради безпеки</Text>
      <Card style={styles.tip}>
        <Ionicons name="timer" size={20} color={c.warning} />
        <View style={styles.flex}>
          <Text style={styles.tipTitle}>Правило двох стін</Text>
          <Text muted style={styles.tipDesc}>
            При тривозі знаходьтесь мінімум за двома капітальними стінами від вулиці
          </Text>
        </View>
      </Card>
      <Card style={styles.tip}>
        <Ionicons name="phone-portrait" size={20} color={c.success} />
        <View style={styles.flex}>
          <Text style={styles.tipTitle}>Зарядіть телефон</Text>
          <Text muted style={styles.tipDesc}>
            Тримайте телефон зарядженим мінімум на 50% для отримання сповіщень
          </Text>
        </View>
      </Card>

      <Text style={styles.section}>Інструменти</Text>
      <Card style={styles.toolsCard}>
        <ToolRow
          icon="medkit"
          title="Медична картка"
          description={medical.bloodType ? `Група крові: ${medical.bloodType}` : 'Заповніть дані для екстрених ситуацій'}
          color={c.danger}
          onPress={() => {
            setDraft(medical);
            setMedicalModal(true);
          }}
        />
        <ToolRow
          icon="call"
          title="Екстрені контакти"
          description={medical.emergencyContact1 || 'Додайте контакти близьких'}
          color={c.danger}
          onPress={() => {
            setDraft(medical);
            setContactsModal(true);
          }}
        />
        <ToolRow
          icon="bag-handle"
          title="Чекліст тривожної валізи"
          description={`${bagChecked} / ${bagTotal} пунктів`}
          color={c.muted}
          onPress={() => setBagModal(true)}
        />
      </Card>

      <MedicalModal
        visible={medicalModal}
        draft={draft}
        onChange={setDraft}
        onClose={() => setMedicalModal(false)}
        onSave={() => {
          safetyStorage.saveMedicalCard(draft);
          setMedical(draft);
          setMedicalModal(false);
        }}
      />
      <ContactsModal
        visible={contactsModal}
        draft={draft}
        onChange={setDraft}
        onClose={() => setContactsModal(false)}
        onSave={() => {
          safetyStorage.saveMedicalCard(draft);
          setMedical(draft);
          setContactsModal(false);
        }}
      />
      <BagModal
        visible={bagModal}
        bag={bag}
        onToggle={(key, value) => {
          const next = { ...bag, [key]: value };
          setBag(next);
          safetyStorage.saveEmergencyBag(next);
        }}
        onClear={() => {
          Alert.alert('Очистити чекліст?', undefined, [
            { text: 'Скасувати', style: 'cancel' },
            {
              text: 'Очистити',
              style: 'destructive',
              onPress: () => {
                setBag({});
                safetyStorage.saveEmergencyBag({});
              },
            },
          ]);
        }}
        onClose={() => setBagModal(false)}
      />
    </ScrollView>
  );
}

function MedicalModal({
  visible,
  draft,
  onChange,
  onClose,
  onSave,
}: {
  visible: boolean;
  draft: MedicalCard;
  onChange: (c: MedicalCard) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  const styles = useScreenStyles();
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalSheet}>
          <Text style={styles.modalTitle}>Медична картка</Text>
          <Field label="Група крові" value={draft.bloodType} onChange={(bloodType) => onChange({ ...draft, bloodType })} placeholder="Напр.: A+ (II+)" />
          <Field label="Алергії" value={draft.allergies} onChange={(allergies) => onChange({ ...draft, allergies })} placeholder="Напр.: Пеніцилін" multiline />
          <Field label="Ліки які приймаю" value={draft.medications} onChange={(medications) => onChange({ ...draft, medications })} placeholder="Напр.: Інсулін" multiline />
          <View style={styles.modalActions}>
            <Pressable onPress={onClose} style={styles.modalGhost}>
              <Text style={styles.modalGhostText}>Скасувати</Text>
            </Pressable>
            <PrimaryButton onPress={onSave}>Зберегти</PrimaryButton>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function ContactsModal({
  visible,
  draft,
  onChange,
  onClose,
  onSave,
}: {
  visible: boolean;
  draft: MedicalCard;
  onChange: (c: MedicalCard) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  const styles = useScreenStyles();
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalSheet}>
          <Text style={styles.modalTitle}>Екстрені контакти</Text>
          <Field label="Контакт 1" value={draft.emergencyContact1} onChange={(emergencyContact1) => onChange({ ...draft, emergencyContact1 })} placeholder="Ім'я та телефон" />
          <Field label="Контакт 2" value={draft.emergencyContact2} onChange={(emergencyContact2) => onChange({ ...draft, emergencyContact2 })} placeholder="Ім'я та телефон" />
          <View style={styles.modalActions}>
            <Pressable onPress={onClose} style={styles.modalGhost}>
              <Text style={styles.modalGhostText}>Скасувати</Text>
            </Pressable>
            <PrimaryButton onPress={onSave}>Зберегти</PrimaryButton>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function BagModal({
  visible,
  bag,
  onToggle,
  onClear,
  onClose,
}: {
  visible: boolean;
  bag: Record<string, boolean>;
  onToggle: (key: string, value: boolean) => void;
  onClear: () => void;
  onClose: () => void;
}) {
  const styles = useScreenStyles();
  const c = useLegacyColors();
  const checked = Object.values(bag).filter(Boolean).length;
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalSheet}>
          <Text style={styles.modalTitle}>Тривожна валіза</Text>
          <Text muted style={styles.bagProgress}>
            {checked} / {EMERGENCY_BAG_CHECKLIST.length}
          </Text>
          <ScrollView style={styles.bagList}>
            {EMERGENCY_BAG_CHECKLIST.map((item) => (
              <View key={item.key} style={styles.bagRow}>
                <Ionicons name={item.icon} size={18} color={c.accent} />
                <Text style={styles.flex}>{item.name}</Text>
                <Switch
                  value={!!bag[item.key]}
                  onValueChange={(v) => onToggle(item.key, v)}
                  trackColor={{ false: c.border, true: c.accent }}
                />
              </View>
            ))}
          </ScrollView>
          <View style={styles.modalActions}>
            <Pressable onPress={onClear} style={styles.modalGhost}>
              <Text style={styles.modalGhostText}>Очистити</Text>
            </Pressable>
            <PrimaryButton onPress={onClose}>Готово</PrimaryButton>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  multiline,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  const styles = useScreenStyles();
  const c = useLegacyColors();
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={c.muted}
        multiline={multiline}
        style={[styles.input, multiline && styles.inputMulti]}
      />
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, backgroundColor: c.bg },
  pad: { padding: spacing.lg, paddingBottom: spacing.xxl, gap: 12 },
  flex: { flex: 1 },
  section: { fontFamily: fonts.bold, fontSize: 18, color: c.text, marginTop: 8 },
  shelterHero: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 18,
    borderRadius: radii.lg,
    backgroundColor: c.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: c.border,
  },
  shelterIcon: {
    padding: 14,
    borderRadius: radii.md,
    backgroundColor: 'rgba(76,201,240,0.15)',
  },
  heroTitle: { fontFamily: fonts.bold, fontSize: 20, color: c.text },
  heroSub: { fontSize: 14, marginTop: 4 },
  tip: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  tipTitle: { fontFamily: fonts.semiBold, fontSize: 15 },
  tipDesc: { fontSize: 13, marginTop: 4, lineHeight: 18 },
  toolsCard: { padding: 0, overflow: 'hidden' },
  toolRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: c.border,
  },
  pressed: { opacity: 0.88 },
  toolIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  toolBody: { flex: 1 },
  toolTitle: { fontFamily: fonts.semiBold, fontSize: 15 },
  toolDesc: { fontSize: 13, marginTop: 2 },
  modalBackdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.55)' },
  modalSheet: {
    maxHeight: '85%',
    backgroundColor: c.surface,
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.lg,
  },
  modalTitle: { fontFamily: fonts.bold, fontSize: 20, marginBottom: 12 },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 12, alignItems: 'center' },
  modalGhost: { paddingVertical: 12, paddingHorizontal: 8 },
  modalGhostText: { color: c.muted, fontFamily: fonts.semiBold },
  field: { marginBottom: 12 },
  fieldLabel: { fontFamily: fonts.semiBold, fontSize: 13, marginBottom: 6, color: c.textSoft },
  input: {
    backgroundColor: c.inputBg,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: c.border,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: c.text,
    fontFamily: fonts.regular,
  },
  inputMulti: { minHeight: 72, textAlignVertical: 'top' },
  bagProgress: { marginBottom: 8 },
  bagList: { maxHeight: 360 },
  bagRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10 },
}));
}
