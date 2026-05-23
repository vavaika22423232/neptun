import { useState } from 'react';
import { ActivityIndicator, Modal, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { Text } from '../../../components/Text';
import { colors, radii } from '../../../theme/colors';
import { fonts } from '../../../theme/fonts';
import { useLegacyScreenStyles } from '../../../theme/useLegacyScreenStyles';

type Props = {
  visible: boolean;
  title: string;
  confirmLabel: string;
  destructive?: boolean;
  onCancel: () => void;
  onConfirm: (secret: string) => Promise<string | null>;
};

export function ModeratorSecretDialog({
  visible,
  title,
  confirmLabel,
  destructive,
  onCancel,
  onConfirm,
}: Props) {
  const styles = useScreenStyles();
const [secret, setSecret] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable style={styles.backdrop} onPress={onCancel}>
        <Pressable style={styles.card} onPress={(e) => e.stopPropagation()}>
          <Text style={styles.title}>{title}</Text>
          <TextInput
            value={secret}
            onChangeText={setSecret}
            secureTextEntry
            placeholder="Пароль"
            placeholderTextColor={colors.muted}
            style={styles.input}
            autoCapitalize="none"
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <View style={styles.actions}>
            <Pressable onPress={onCancel} style={styles.btnGhost}>
              <Text>Скасувати</Text>
            </Pressable>
            <Pressable
              disabled={busy}
              onPress={() => {
                setBusy(true);
                setError(null);
                void onConfirm(secret).then((err) => {
                  setBusy(false);
                  if (typeof err === 'string' && err) setError(err);
                  else {
                    setSecret('');
                    onCancel();
                  }
                });
              }}
              style={[styles.btnPrimary, destructive && styles.btnDanger]}
            >
              {busy ? <ActivityIndicator color={colors.text} /> : <Text style={styles.btnPrimaryText}>{confirmLabel}</Text>}
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    borderRadius: radii.lg,
    backgroundColor: c.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: c.borderStrong,
    padding: 18,
    gap: 12,
  },
  title: {
    fontFamily: fonts.bold,
    fontSize: 17,
  },
  input: {
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: c.border,
    backgroundColor: c.inputBg,
    color: c.text,
    fontFamily: fonts.medium,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  error: {
    color: c.danger,
    fontSize: 13,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 4,
  },
  btnGhost: {
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  btnPrimary: {
    minWidth: 100,
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: radii.md,
    backgroundColor: c.accent,
  },
  btnDanger: {
    backgroundColor: c.danger,
  },
  btnPrimaryText: {
    fontFamily: fonts.bold,
    color: '#04111B',
  },
}));
}
