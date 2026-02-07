// SSE stream for real-time chat events
// Flutter connects here for new_message, delete_message, typing, reaction events

const clients = new Set<ReadableStreamDefaultController>();

// Broadcast an event to all connected SSE clients
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function broadcastSSE(event: { type: string; data: any }) {
  const payload = `data: ${JSON.stringify(event)}\n\n`;
  const deadClients: ReadableStreamDefaultController[] = [];

  clients.forEach((controller) => {
    try {
      controller.enqueue(new TextEncoder().encode(payload));
    } catch {
      deadClients.push(controller);
    }
  });

  // Clean up dead connections
  deadClients.forEach((c) => clients.delete(c));
}

export async function GET() {
  const stream = new ReadableStream({
    start(controller) {
      clients.add(controller);

      // Send keepalive every 30s
      const keepalive = setInterval(() => {
        try {
          controller.enqueue(new TextEncoder().encode(': keepalive\n\n'));
        } catch {
          clearInterval(keepalive);
          clients.delete(controller);
        }
      }, 30_000);

      // Send initial connection event
      try {
        controller.enqueue(
          new TextEncoder().encode(
            `data: ${JSON.stringify({ type: 'connected', data: { online: clients.size } })}\n\n`
          )
        );
      } catch { /* ignore */ }
    },
    cancel() {
      // Client disconnected — cleaned up on next broadcast
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
