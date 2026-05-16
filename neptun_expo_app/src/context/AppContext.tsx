import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { endpoints } from '../config/api';
import { chatService } from '../services/chatService';
import { purchaseService } from '../services/purchaseService';
import { storage } from '../services/storage';
import { apiRequest } from '../services/apiClient';
import { hydrateSleepMode } from '../services/sleepModeStore';
import { parseAlarmsPayload, syncAlarmStatsFromRows } from '../services/alarmStatsService';

type AppState = {
  deviceId: string | null;
  nickname: string | null;
  isPremium: boolean;
  isModerator: boolean;
  onlineCount: number;
  setNickname: (nickname: string | null) => void;
  setPremium: (value: boolean) => Promise<void>;
  refreshIdentity: () => Promise<void>;
  setOnlineCount: (n: number) => void;
};

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [nickname, setNicknameState] = useState<string | null>(null);
  const [isPremium, setPremiumState] = useState(false);
  const [isModerator, setModerator] = useState(false);
  const [onlineCount, setOnlineCount] = useState(0);

  async function refreshIdentity() {
    const boot = await chatService.bootstrap();
    setDeviceId(boot.deviceId);
    setNicknameState(boot.nickname);
    setPremiumState(await purchaseService.isPremium());
    setModerator(!!(await storage.getModeratorSecret()));
  }

  useEffect(() => {
    refreshIdentity().catch(() => undefined);
    void hydrateSleepMode();
    void (async () => {
      try {
        const data = await apiRequest<unknown>(endpoints.alarmsAll, { timeoutMs: 15_000 });
        await syncAlarmStatsFromRows(parseAlarmsPayload(data));
      } catch {
        /* offline */
      }
    })();
    const id = setInterval(() => {
      void (async () => {
        try {
          const data = await apiRequest<unknown>(endpoints.alarmsAll, { timeoutMs: 15_000 });
          await syncAlarmStatsFromRows(parseAlarmsPayload(data));
        } catch {
          /* ignore */
        }
      })();
    }, 180_000);
    return () => clearInterval(id);
  }, []);

  const value = useMemo<AppState>(
    () => ({
      deviceId,
      nickname,
      isPremium,
      isModerator,
      onlineCount,
      setNickname: setNicknameState,
      async setPremium(value) {
        await (value ? purchaseService.enableLocalPro() : purchaseService.disableLocalPro());
        setPremiumState(value);
      },
      refreshIdentity,
      setOnlineCount,
    }),
    [deviceId, nickname, isPremium, isModerator, onlineCount],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside AppProvider');
  return ctx;
}
