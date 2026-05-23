import { useRouter } from 'expo-router';
import { useEffect } from 'react';
import { useApp } from '../../context/AppContext';

/** Redirect non-moderators away from moderation screens (UX guard; API still enforces auth). */
export function useModeratorScreenGuard(): boolean {
  const { isModerator } = useApp();
  const router = useRouter();

  useEffect(() => {
    if (!isModerator) {
      router.replace('/');
    }
  }, [isModerator, router]);

  return isModerator;
}
