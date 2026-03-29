import { Suspense } from 'react';
import ChatClient from './ChatClient';

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="w-full h-full bg-[var(--surface)]" />}>
      <ChatClient />
    </Suspense>
  );
}
