import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadSettings, saveSettings } from '@/lib/admin/data';
import { invalidateMarkerDerivedCaches } from '@/lib/cache';

export async function POST(request: Request) {
    const denied = await requireAdminAuth();
    if (denied) return denied;

    try {
        const { value } = await request.json();
        if (typeof value !== 'number' || value < 0 || value > 1) {
            return NextResponse.json({ error: 'Invalid confidence value (must be 0-1)' }, { status: 400 });
        }

        const settings = loadSettings();
        settings.minConfidence = value;
        saveSettings(settings);

        invalidateMarkerDerivedCaches();

        return NextResponse.json({ success: true, minConfidence: value });
    } catch (error) {
        console.error('Failed to save minConfidence:', error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
