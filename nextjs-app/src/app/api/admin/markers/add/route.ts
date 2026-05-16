import { NextResponse } from 'next/server';
import crypto from 'crypto';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { ingestMarkerEvidence } from '@/lib/tracked-target-store';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { lat, lng, text, place, threat_type, icon, rotation, trajectory, course_direction, course_target, course_source, course_type } = body;

    if (!lat || !lng || lat < 43 || lat > 53.8 || lng < 21 || lng > 41.5) {
      return NextResponse.json({ error: 'Invalid coordinates' }, { status: 400 });
    }

    const newMarker = {
      id: crypto.randomBytes(6).toString('hex'),
      lat: Number(lat),
      lng: Number(lng),
      text: text || '',
      place: place || '',
      threat_type: threat_type || 'manual',
      marker_icon: icon || '',
      rotation: rotation || 0,
      date: new Date().toISOString(),
      manual: true,
      count: 1,
      trajectory: trajectory || null,
      course_direction: course_direction || '',
      course_target: course_target || '',
      course_source: course_source || '',
      course_type: course_type || '',
    };

    await ingestMarkerEvidence(newMarker);

    return NextResponse.json({ status: 'ok', marker: newMarker });
  } catch (err) {
    console.error('[ADMIN ADD MARKER]', err);
    return NextResponse.json({ error: 'Failed to add marker' }, { status: 500 });
  }
}
