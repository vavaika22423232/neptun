import { create } from 'zustand';
import { storage } from '../../../services/storage';

const STORAGE_KEY = 'chat_prefs_v1';

type Persisted = {
  pinnedMessageIds: string[];
  draft: string;
};

type State = {
  hydrated: boolean;
  pinnedMessageIds: string[];
  draft: string;
};

type Actions = {
  hydrate: () => Promise<void>;
  persist: () => Promise<void>;
  pinMessage: (messageId: string) => void;
  unpinMessage: (messageId: string) => void;
  setDraft: (text: string) => void;
  clearDraft: () => void;
};

export const useChatPrefsStore = create<State & Actions>((set, get) => ({
  hydrated: false,
  pinnedMessageIds: [],
  draft: '',

  async hydrate() {
    const raw = await storage.getJson<Persisted>(STORAGE_KEY, {
      pinnedMessageIds: [],
      draft: '',
    });
    set({ hydrated: true, pinnedMessageIds: raw.pinnedMessageIds, draft: raw.draft });
  },

  async persist() {
    const s = get();
    await storage.setJson(STORAGE_KEY, {
      pinnedMessageIds: s.pinnedMessageIds,
      draft: s.draft,
    });
  },

  pinMessage(messageId) {
    const ids = get().pinnedMessageIds;
    if (ids.includes(messageId)) return;
    set({ pinnedMessageIds: [messageId, ...ids].slice(0, 40) });
    void get().persist();
  },

  unpinMessage(messageId) {
    set({ pinnedMessageIds: get().pinnedMessageIds.filter((x) => x !== messageId) });
    void get().persist();
  },

  setDraft(draft) {
    set({ draft });
    void get().persist();
  },

  clearDraft() {
    set({ draft: '' });
    void get().persist();
  },
}));
