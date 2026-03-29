import { NextResponse } from 'next/server';
import { loadSettings } from '@/lib/admin/data';

// Public endpoint for the Python Worker to fetch active global settings
// In the future this could be protected by the X-Auth-Secret if needed.
export async function GET() {
    try {
        const settings = loadSettings();
        return NextResponse.json({
            minConfidence: settings.minConfidence ?? 0.3,
            monitorPeriod: settings.monitorPeriod ?? 30,
        });
    } catch (error) {
        console.error('Failed to load settings API:', error);
        return NextResponse.json({ minConfidence: 0.3 }, { status: 500 });
    }
}
