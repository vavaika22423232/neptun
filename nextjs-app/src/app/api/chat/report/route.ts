import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { requireChatAuth } from '@/lib/chat-auth';
import { anonymousGuestLabel } from '@/lib/chat-nicknames';
import { ChatReportSchema } from '@/lib/api-schemas';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';

const DATA_DIR = process.env.DATA_DIR || '/data';
const REPORTS_FILE = path.join(DATA_DIR, 'chat_reports.json');
const FALLBACK_REPORTS_FILE = path.resolve(process.cwd(), '..', 'chat_reports.json');

const MAX_REPORTS = 500;

function resolveReportsFile(): string {
  for (const dir of [DATA_DIR, path.dirname(FALLBACK_REPORTS_FILE)]) {
    try {
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      fs.accessSync(dir, fs.constants.W_OK);
      return dir === DATA_DIR ? REPORTS_FILE : FALLBACK_REPORTS_FILE;
    } catch { /* try next */ }
  }
  return FALLBACK_REPORTS_FILE;
}

export async function POST(request: Request) {
  try {
    const authResult = requireChatAuth(request);
    if (authResult instanceof Response) return authResult;

    const ip = getClientIp(request);
    const deviceTag = authResult.deviceId.slice(0, 12);
    const allowed = await redisFixedWindowAllow(
      `rl:chat:report:${ipRedisTag(ip)}:${deviceTag}`,
      8,
      3600,
      false,
    );
    if (!allowed) {
      logSecurityEvent('rate_limit_hit', { route: 'chat_report' });
      return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
    }

    const parsed = ChatReportSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
    }

    const { messageId, reason, originalText, reportedDeviceId, reportedNickname } = parsed.data;
    const reporterDeviceId = authResult.deviceId;
    const reporterNickname = authResult.nickname;

    const filePath = resolveReportsFile();
    let reports: unknown[] = [];

    try {
      if (fs.existsSync(filePath)) {
        const raw = await fsp.readFile(filePath, 'utf-8');
        reports = JSON.parse(raw);
        if (!Array.isArray(reports)) reports = [];
      }
    } catch (e) {
      console.error('Error reading reports file:', e);
      reports = [];
    }

    const newReport = {
      id: crypto.randomUUID(),
      messageId,
      reason,
      reporterDeviceId,
      reporterNickname: reporterNickname || anonymousGuestLabel(reporterDeviceId),
      originalText: originalText || '',
      reportedDeviceId: reportedDeviceId || '',
      reportedNickname:
        reportedNickname ||
        (reportedDeviceId ? anonymousGuestLabel(String(reportedDeviceId)) : 'Гість'),
      status: 'PENDING',
      createdAt: new Date().toISOString(),
    };

    reports.push(newReport);

    if (reports.length > MAX_REPORTS) {
      reports = reports.slice(-MAX_REPORTS);
    }

    const tmp = `${filePath}.tmp.${crypto.randomBytes(4).toString('hex')}`;
    await fsp.writeFile(tmp, JSON.stringify(reports, null, 2), 'utf-8');
    await fsp.rename(tmp, filePath);

    return NextResponse.json({ status: 'ok', success: true });
  } catch (err) {
    console.error('[CHAT_REPORT] Send error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
