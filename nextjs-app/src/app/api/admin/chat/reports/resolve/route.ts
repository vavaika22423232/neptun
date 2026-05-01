import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { recordViolation } from '@/lib/chat-violations';

const DATA_DIR = process.env.DATA_DIR || '/data';
const REPORTS_FILE = path.join(DATA_DIR, 'chat_reports.json');
const FALLBACK_REPORTS_FILE = path.resolve(process.cwd(), '..', 'chat_reports.json');

type ChatReportRecord = {
    id: string;
    status?: string;
    resolvedAt?: string;
    reportedDeviceId?: string;
    reportedNickname?: string;
};

function resolveReportsFile(): string {
    if (!fs.existsSync(DATA_DIR)) {
        try {
            fs.mkdirSync(DATA_DIR, { recursive: true });
        } catch { }
    }
    return fs.existsSync(DATA_DIR) ? REPORTS_FILE : FALLBACK_REPORTS_FILE;
}

export async function POST(request: Request) {
    const authResponse = await requireAdminAuth();
    if (authResponse) return authResponse;

    try {
        const { reportId, action } = await request.json();
        if (!reportId || !['RESOLVED', 'REJECTED'].includes(action)) {
            return NextResponse.json({ error: 'Invalid action or missing reportId' }, { status: 400 });
        }

        const filePath = resolveReportsFile();
        if (!fs.existsSync(filePath)) {
            return NextResponse.json({ error: 'No reports found' }, { status: 404 });
        }

        const raw = await fsp.readFile(filePath, 'utf-8');
        const parsed = JSON.parse(raw) as unknown;
        const reports: ChatReportRecord[] = Array.isArray(parsed) ? parsed as ChatReportRecord[] : [];

        const reportIndex = reports.findIndex((r) => r.id === reportId);
        if (reportIndex === -1) {
            return NextResponse.json({ error: 'Report not found' }, { status: 404 });
        }

        const report = reports[reportIndex];
        reports[reportIndex].status = action;
        reports[reportIndex].resolvedAt = new Date().toISOString();

        if (action === 'RESOLVED' && report.reportedDeviceId && report.reportedNickname) {
            const { count, autoBanned } = recordViolation(
                report.reportedDeviceId,
                report.reportedNickname
            );
            if (autoBanned) {
                console.log(
                    `[CHAT] Auto-banned ${report.reportedNickname} (${report.reportedDeviceId?.slice(0, 8)}…) after ${count} violations`
                );
            }
        }

        const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
        await fsp.writeFile(tmp, JSON.stringify(reports, null, 2), 'utf-8');
        await fsp.rename(tmp, filePath);

        return NextResponse.json({ status: 'ok', success: true });
    } catch (err) {
        console.error('[ADMIN_REPORTS_RESOLVE_ERROR]', err);
        return NextResponse.json({ error: 'Internal Error' }, { status: 500 });
    }
}
