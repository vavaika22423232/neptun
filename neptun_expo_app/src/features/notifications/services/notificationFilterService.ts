export type NotificationEvent = {
  oblastId?: string;
  raionId?: string;
  settlementId?: string;
};

export type UserRegionSelection = {
  oblastIds: Set<string>;
  raionIds: Set<string>;
  settlementId: string | null;
};

/** Flutter `NotificationFilterService.shouldShowNotification`. */
export function shouldShowNotification(
  event: NotificationEvent,
  user: UserRegionSelection,
): boolean {
  if (user.oblastIds.size === 0 && user.raionIds.size === 0 && !user.settlementId) {
    return false;
  }
  if (!event.oblastId?.trim()) return false;

  if (user.settlementId) {
    return event.settlementId === user.settlementId;
  }

  if (user.raionIds.size > 0) {
    if (event.raionId?.trim()) {
      return user.raionIds.has(event.raionId);
    }
    return false;
  }

  if (user.oblastIds.size > 0) {
    return user.oblastIds.has(event.oblastId);
  }

  return false;
}
