import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

const DATA_DIR = process.env.DATA_DIR || '/data';
const REPORTS_FILE = path.join(DATA_DIR, 'chat_reports.json');
const FALLBACK_REPORTS_FILE = path.resolve(process.cwd(), '..', 'chat_reports.json');
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

function resolveReportsFile(): string {
    if (!fs.existsSync(DATA_DIR)) {
        try {
            fs.mkdirSync(DATA_DIR, { recursive: true });
        } catch { }
    }
    return fs.existsSync(DATA_DIR) ? REPORTS_FILE : FALLBACK_REPORTS_FILE;
}

async function loadChatMessages(): Promise<Record<string, unknown>[]> {
    for (const filePath of [CHAT_FILE, FALLBACK_CHAT_FILE]) {
        try {
            if (fs.existsSync(filePath)) {
                const raw = await fsp.readFile(filePath, 'utf-8');
                const data = JSON.parse(raw);
                const messages = Array.isArray(data) ? data : data.messages || [];
                return messages as Record<string, unknown>[];
            }
        } catch { /* try next */ }
    }
    return [];
}

export async function GET() {
    const authResponse = await requireAdminAuth();
    if (authResponse) return authResponse;

    try {
        const filePath = resolveReportsFile();
        let reports: Record<string, unknown>[] = [];

        if (fs.existsSync(filePath)) {
            const raw = await fsp.readFile(filePath, 'utf-8');
            reports = JSON.parse(raw);
            if (!Array.isArray(reports)) reports = [];
        }

        // Enrich reports with message media (imageUrl, audioUrl) from chat_messages
        const messages = await loadChatMessages();
        const msgById = new Map<string, Record<string, unknown>>();
        for (const m of messages) {
            const id = m.id as string;
            if (id) msgById.set(id, m);
        }
        reports = reports.map((r) => {
            const msg = msgById.get(r.messageId as string);
            if (!msg) return r;
            return {
                ...r,
                imageUrl: msg.imageUrl ?? msg.image_url ?? null,
                audioUrl: msg.audioUrl ?? msg.audio_url ?? null,
                messageType: msg.messageType ?? msg.message_type ?? 'text',
                audioDuration: msg.audioDuration ?? msg.audio_duration ?? null,
            };
        });

        // Return the reports, sorted by newest first
        reports.sort((a, b) => {
            const dateA = new Date(a.createdAt as string || 0).getTime();
            const dateB = new Date(b.createdAt as string || 0).getTime();
            return dateB - dateA; // descending
        });

        return NextResponse.json({ status: 'ok', reports });
    } catch (err) {
        console.error('[ADMIN_REPORTS_ERROR]', err);
        return NextResponse.json({ error: 'Internal Error' }, { status: 500 });
    }
}
