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
    if (!fs.existsSync(DATA_DIR)) {
        try {
            fs.mkdirSync(DATA_DIR, { recursive: true });
        } catch { }
    }
    return fs.existsSync(DATA_DIR) ? REPORTS_FILE : FALLBACK_REPORTS_FILE;
}

export async function POST(request: Request) {
    try {
        const body = await request.json();

        const {
            messageId,
            reason,
            reporterDeviceId,
            reporterNickname,
            originalText,
            reportedDeviceId,
            reportedNickname,
        } = body;

        if (!messageId || !reason || !reporterDeviceId) {
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
