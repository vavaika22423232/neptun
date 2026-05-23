import { Ionicons } from '@expo/vector-icons';
import { ActivityIndicator, Platform, StyleSheet, TextInput, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import type { ChatMessage } from '../../../types/chat';

const MAX_MESSAGE = 500;

type Props = {
  text: string;
  replyTo: ChatMessage | null;
  editing: ChatMessage | null;
  isSending: boolean;
  recording: boolean;
  recordingSeconds: number;
  bottomInset?: number;
  onChangeText: (value: string) => void;
  onSend: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onCancelRecording: () => void;
  onAttach: () => void;
  onDismissReply: () => void;
  onDismissEdit: () => void;
};

/** Dark pill composer — reference messenger style. */
export function ChatComposer({
  text,
  replyTo,
  editing,
  isSending,
  recording,
  recordingSeconds,
  onChangeText,
  onSend,
  onStartRecording,
  onStopRecording,
  onCancelRecording,
  onAttach,
  onDismissReply,
  onDismissEdit,
  bottomInset = 0,
}: Props) {
  const { theme } = useAppTheme();
  const ch = theme.chat;
  const styles = useComposerStyles();
  const canSend = !!text.trim();

  const shellStyle = [styles.shell, { paddingBottom: bottomInset > 0 ? bottomInset : 10 }];

  if (recording) {
    return (
      <View style={shellStyle}>
        <View style={styles.pill}>
          <NeptunPressable haptic onPress={onCancelRecording} style={styles.attachBtn}>
            <Ionicons name="trash-outline" size={20} color={ch.danger} />
          </NeptunPressable>
          <View style={styles.recordDot} />
          <Text style={styles.recordTime}>
            {Math.floor(recordingSeconds / 60)}:{String(recordingSeconds % 60).padStart(2, '0')}
          </Text>
          <View style={styles.flex} />
          <NeptunPressable haptic onPress={onStopRecording} style={styles.sendHit}>
            <Ionicons name="send" size={20} color={ch.text} />
          </NeptunPressable>
        </View>
      </View>
    );
  }

  return (
    <View style={shellStyle}>
      {editing || replyTo ? (
        <View style={styles.preview}>
          <View style={styles.previewAccent} />
          <View style={styles.previewBody}>
            <Text style={styles.previewTitle}>{editing ? 'Редагування' : replyTo?.userId}</Text>
            <Text muted numberOfLines={1} style={styles.previewText}>
              {editing?.message || replyTo?.message}
            </Text>
          </View>
          <NeptunPressable haptic onPress={editing ? onDismissEdit : onDismissReply} style={styles.attachBtn}>
            <Ionicons name="close" size={18} color={ch.textMuted} />
          </NeptunPressable>
        </View>
      ) : null}
      <View style={styles.pill}>
        <NeptunPressable haptic onPress={onAttach} style={styles.attachBtn}>
          <Ionicons name="add" size={26} color={ch.textSoft} />
        </NeptunPressable>
        <TextInput
          value={text}
          onChangeText={onChangeText}
          placeholder="Надіслати повідомлення"
          placeholderTextColor={ch.textMuted}
          style={styles.input}
          multiline
          maxLength={MAX_MESSAGE}
        />
        <NeptunPressable
          haptic
          onPress={canSend ? onSend : onStartRecording}
          onLongPress={onStartRecording}
          disabled={isSending}
          style={styles.sendHit}
        >
          {isSending ? (
            <ActivityIndicator size="small" color={ch.textSoft} />
          ) : (
            <Ionicons
              name={canSend ? 'send' : 'mic-outline'}
              size={20}
              color={canSend ? ch.text : ch.textMuted}
            />
          )}
        </NeptunPressable>
      </View>
    </View>
  );
}

function useComposerStyles() {
  return useThemedStyles((t) => {
    const c = t.chat;
    const isDark = t.scheme === 'dark';
    const pillBg = isDark ? '#1C1C1E' : '#E9E9EB';
    const attachBg = isDark ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.06)';
    return StyleSheet.create({
      shell: {
        paddingHorizontal: 14,
        paddingTop: 6,
        backgroundColor: 'transparent',
      },
      flex: { flex: 1 },
      pill: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        minHeight: 54,
        paddingLeft: 6,
        paddingRight: 12,
        paddingVertical: 8,
        borderRadius: c.radiusComposer,
        backgroundColor: pillBg,
      },
      attachBtn: {
        width: 38,
        height: 38,
        borderRadius: 19,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: attachBg,
      },
      sendHit: {
        width: 38,
        height: 38,
        alignItems: 'center',
        justifyContent: 'center',
      },
      input: {
        flex: 1,
        fontFamily: fonts.regular,
        fontSize: 16,
        lineHeight: 20,
        color: c.text,
        paddingTop: Platform.OS === 'ios' ? 10 : 8,
        paddingBottom: Platform.OS === 'ios' ? 8 : 8,
        maxHeight: 108,
        minHeight: 38,
        ...(Platform.OS === 'android' ? { textAlignVertical: 'center' as const, includeFontPadding: false } : {}),
      },
      preview: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingHorizontal: 4,
        paddingBottom: 8,
      },
      previewAccent: {
        width: 2,
        alignSelf: 'stretch',
        borderRadius: 1,
        backgroundColor: c.accent,
      },
      previewBody: { flex: 1, minWidth: 0 },
      previewTitle: { fontFamily: fonts.semiBold, fontSize: 11, color: c.accentSoft },
      previewText: { fontSize: 12, marginTop: 1, color: c.textSoft },
      recordDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: c.danger,
      },
      recordTime: { fontFamily: fonts.semiBold, fontSize: 15, color: c.text },
    });
  });
}
