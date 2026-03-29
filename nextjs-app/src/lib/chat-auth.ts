import crypto from 'crypto';

export function verifyChatToken(token: string, secret: string) {
  try {
    const [hBase64, pBase64, signature] = token.split('.');
    if (!hBase64 || !pBase64 || !signature) return null;
    
    const data = `${hBase64}.${pBase64}`;
    const expectedSig = crypto.createHmac('sha256', secret).update(data).digest('base64url');
    if (signature !== expectedSig) return null;
    
    const payload = JSON.parse(Buffer.from(pBase64, 'base64url').toString('utf-8'));
    if (Date.now() / 1000 > payload.exp) return null;
    return payload;
  } catch { return null; }
}
