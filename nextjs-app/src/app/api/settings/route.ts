import { NextResponse } from 'next/server';
import { loadSettings } from '@/lib/admin/data';
import { getAdminHeaderSecret, safeCompare } from '@/lib/server-secrets';

export async function GET(request: Request) {
    const secret = request.headers.get('X-Auth-Secret') || '';
    const expected = getAdminHeaderSecret();
    if (!expected || !secret || !safeCompare(secret, expected)) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        const settings = loadSettings();
        return NextResponse.json({
            minConfidence: settings.minConfidence ?? 0.65,
            minConfidenceUav: settings.minConfidenceUav ?? null,
            monitorPeriod: settings.monitorPeriod ?? 30,
        });
    } catch (error) {
        console.error('Failed to load settings API:', error);
        return NextResponse.json({ minConfidence: 0.65 }, { status: 500 });
    }
}
