import { memo } from 'react';
import { View } from 'react-native';
import { OfflineBanner } from './OfflineBanner';
import { ChatTabHeader } from '../features/chat/components/ChatTabHeader';

function ChatTabChromeInner() {
  return (
    <View>
      <ChatTabHeader />
      <OfflineBanner />
    </View>
  );
}

export const ChatTabChrome = memo(ChatTabChromeInner);
