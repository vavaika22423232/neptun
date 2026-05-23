import { useCallback, useRef, useState } from 'react';
import { moderatorService } from '../../services/moderatorService';

const TAP_WINDOW_MS = 3000;
const TAP_TARGET = 7;

export function useModeratorLogoTap() {
  const countRef = useRef(0);
  const lastTapRef = useRef(0);
  const [showLogin, setShowLogin] = useState(false);
  const [showLogout, setShowLogout] = useState(false);

  const onLogoTap = useCallback(() => {
    const now = Date.now();
    if (now - lastTapRef.current > TAP_WINDOW_MS) countRef.current = 0;
    lastTapRef.current = now;
    countRef.current += 1;
    if (countRef.current < TAP_TARGET) return;
    countRef.current = 0;
    void moderatorService.isModerator().then((isMod) => {
      if (isMod) setShowLogout(true);
      else setShowLogin(true);
    });
  }, []);

  return { onLogoTap, showLogin, setShowLogin, showLogout, setShowLogout };
}
