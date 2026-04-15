import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';

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

import { requireChatAuth } from '@/lib/chat-auth';

export async function POST(request: Request) {
    try {
        const authResult = requireChatAuth(request);
        if (authResult instanceof Response) return authResult;

        const body = await request.json();

        const {
            messageId,
            reason,
            originalText,
            reportedDeviceId,
            reportedNickname,
        } = body;

        const reporterDeviceId = authResult.deviceId;
        const reporterNickname = authResult.nickname;

        if (!messageId || !reason) {
            return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
        }

        const filePath = resolveReportsFile();
        let reports = [];

        // Load existing reports
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

        // Add new report
        const newReport = {
            id: crypto.randomUUID(),
            messageId,
            reason,
            reporterDeviceId,
            reporterNickname: reporterNickname || 'Анонім',
            originalText: originalText || '',
            reportedDeviceId: reportedDeviceId || '',
            reportedNickname: reportedNickname || 'Анонім',
            status: 'PENDING',
            createdAt: new Date().toISOString(),
        };

        reports.push(newReport);

        // Keep only latest MAX_REPORTS
        if (reports.length > MAX_REPORTS) {
            reports = reports.slice(-MAX_REPORTS);
        }

        // Atomic write
        const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
        await fsp.writeFile(tmp, JSON.stringify(reports, null, 2), 'utf-8');
        await fsp.rename(tmp, filePath);

        return NextResponse.json({ status: 'ok', success: true });
    } catch (err) {
        console.error('[CHAT_REPORT] Send error:', err);
        return NextResponse.json({ error: 'Internal error' }, { status: 500 });
    }
}
