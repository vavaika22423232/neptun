import { ScrollView, StyleSheet } from 'react-native';
import { NeptunFilterPill } from '../../../../design/components/NeptunFilterPill';

const DEFAULT_REPLIES = ['Дякую!', 'Уточнюю…', 'Підтверджую', 'Будьте обережні', '🇺🇦'];

type Props = {
  visible: boolean;
  onPick: (text: string) => void;
};

export function ChatSmartReplies({ visible, onPick }: Props) {
  if (!visible) return null;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      {DEFAULT_REPLIES.map((r) => (
        <NeptunFilterPill key={r} label={r} onPress={() => onPick(r)} />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: 8, paddingHorizontal: 14, paddingBottom: 6 },
});
