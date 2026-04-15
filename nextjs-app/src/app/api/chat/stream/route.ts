// SSE stream for real-time chat — implementation in `@/lib/chat-sse-stream`.
// This file only exports route handlers so Next.js App Router typegen stays valid.

import { handleChatSSEGet } from '@/lib/chat-sse-stream';

export async function GET(request: Request) {
  return handleChatSSEGet(request);
}
