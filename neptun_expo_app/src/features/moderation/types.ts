export type ChatReportStatus = 'PENDING' | 'RESOLVED' | 'REJECTED' | string;

export type ChatReport = {
  id: string;
  messageId: string;
  reason: string;
  reporterNickname: string;
  reportedNickname: string;
  reportedDeviceId: string;
  originalText: string;
  status: ChatReportStatus;
  createdAt: string;
  imageUrl?: string;
  audioUrl?: string;
  messageType: string;
  audioDuration?: number;
};

export type FeedbackTicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed' | string;

export type FeedbackResponse = {
  author?: string;
  message?: string;
  created_at?: string;
};

export type FeedbackTicket = {
  id: string;
  message: string;
  type: string;
  status: FeedbackTicketStatus;
  device_id: string;
  device: string;
  app_version: string;
  created_at: string;
  responses: FeedbackResponse[];
};

export function parseChatReport(json: Record<string, unknown>): ChatReport {
  const dur = json.audioDuration;
  return {
    id: String(json.id ?? ''),
    messageId: String(json.messageId ?? ''),
    reason: String(json.reason ?? ''),
    reporterNickname: String(json.reporterNickname ?? 'Анонім'),
    reportedNickname: String(json.reportedNickname ?? 'Анонім'),
    reportedDeviceId: String(json.reportedDeviceId ?? ''),
    originalText: String(json.originalText ?? ''),
    status: String(json.status ?? 'PENDING'),
    createdAt: String(json.createdAt ?? ''),
    imageUrl: json.imageUrl != null ? String(json.imageUrl) : undefined,
    audioUrl: json.audioUrl != null ? String(json.audioUrl) : undefined,
    messageType: String(json.messageType ?? 'text'),
    audioDuration:
      typeof dur === 'number' ? dur : typeof dur === 'string' ? Number.parseInt(dur, 10) || undefined : undefined,
  };
}

export function parseFeedbackTicket(json: Record<string, unknown>): FeedbackTicket {
  const responses = Array.isArray(json.responses)
    ? json.responses.map((r) => (typeof r === 'object' && r ? (r as FeedbackResponse) : {}))
    : [];
  return {
    id: String(json.id ?? ''),
    message: String(json.message ?? ''),
    type: String(json.type ?? 'general'),
    status: String(json.status ?? 'open'),
    device_id: String(json.device_id ?? ''),
    device: String(json.device ?? ''),
    app_version: String(json.app_version ?? ''),
    created_at: String(json.created_at ?? ''),
    responses,
  };
}
