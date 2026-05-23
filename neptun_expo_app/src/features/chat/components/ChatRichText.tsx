import * as Linking from 'expo-linking';
import { StyleSheet, Text as RNText } from 'react-native';
import { fonts } from '../../../theme/fonts';
import { useAppTheme } from '../../../theme/useAppTheme';
import { parseRichText } from '../utils/parseRichText';

type Props = {
  text: string;
  color: string;
  style?: object;
};

export function ChatRichText({ text, color, style }: Props) {
  const { theme } = useAppTheme();
  const ch = theme.chat;
  const segments = parseRichText(text);

  return (
    <RNText style={[styles.base, { color }, style]}>
      {segments.map((seg, i) => {
        if (seg.type === 'mention') {
          return (
            <RNText key={i} style={[styles.mention, { color: ch.accentSoft }]} onPress={() => undefined}>
              {seg.value}
            </RNText>
          );
        }
        if (seg.type === 'hashtag') {
          return (
            <RNText key={i} style={[styles.hashtag, { color: ch.premium }]}>
              {seg.value}
            </RNText>
          );
        }
        if (seg.type === 'url') {
          return (
            <RNText key={i} style={[styles.link, { color: ch.accentSoft }]} onPress={() => void Linking.openURL(seg.value)}>
              {seg.value}
            </RNText>
          );
        }
        return (
          <RNText key={i} style={{ color }}>
            {seg.value}
          </RNText>
        );
      })}
    </RNText>
  );
}

const styles = StyleSheet.create({
  base: { fontFamily: fonts.medium, fontSize: 16, lineHeight: 23 },
  mention: { fontFamily: fonts.semiBold },
  hashtag: { fontFamily: fonts.semiBold },
  link: { textDecorationLine: 'underline' },
});
