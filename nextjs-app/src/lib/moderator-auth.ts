import { NextResponse } from 'next/server';
import { requireAdminAuth } from './admin/apiAuth';
import { isModeratorDevice } from './admin/data';
import { requireChatAuth, type ChatIdentity } from './chat-auth';

export type ModeratorAuth =
  | { ok: true; via: 'admin' }
  | { ok: true; via: 'moderator'; identity: ChatIdentity }
  | { ok: false; response: NextResponse };

/**
 * Moderation actions require admin session/secret OR a JWT belonging to a registered moderator device.
 * Device id alone is not sufficient.
 */
export async function requireModeratorAuth(request: Request): Promise<ModeratorAuth> {
  const adminErr = await requireAdminAuth();
  if (adminErr === null) {
    return { ok: true, via: 'admin' };
  }

  const auth = requireChatAuth(request);
  if (auth instanceof Response) {
    return { ok: false, response: auth };
  }

  if (!isModeratorDevice(auth.deviceId)) {
    return {
      ok: false,
      response: NextResponse.json({ error: 'Доступ заборонено' }, { status: 403 }),
    };
  }

  return { ok: true, via: 'moderator', identity: auth };
}
