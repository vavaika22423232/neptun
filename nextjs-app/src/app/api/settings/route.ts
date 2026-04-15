import { NextResponse } from 'next/server';
import { loadSettings } from '@/lib/admin/data';

export async function GET(request: Request) {
    const secret = request.headers.get('X-Auth-Secret') || '';
    const expected = process.env.ADMIN_SECRET || process.env.AUTH_SECRET || '';
    if (!expected || secret !== expected) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        const settings = loadSettings();
        return NextResponse.json({
            minConfidence: settings.minConfidence ?? 0.65,
            monitorPeriod: settings.monitorPeriod ?? 30,
        });
    } catch (error) {
        console.error('Failed to load settings API:', error);
        return NextResponse.json({ minConfidence: 0.65 }, { status: 500 });
    }
}
