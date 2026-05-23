export type ReactionInfo = {
  deviceId: string;
  nickname: string;
  timestamp: number;
};

export type ReplyInfo = {
  id: string;
  nickname?: string | null;
  text?: string | null;
};

export type ChatMessage = {
  id: string;
  userId: string;
  deviceId: string;
  message: string;
  timestamp: number;
  time?: string;
  date?: string;
  isModerator: boolean;
  isPro: boolean;
  replyTo?: ReplyInfo | null;
  reactions: Record<string, ReactionInfo[]>;
  messageType: 'text' | 'voice' | 'image' | string;
  audioUrl?: string | null;
  audioDuration?: number | null;
  imageUrl?: string | null;
  editedAt?: number | null;
};
